"""Parallel directory scanner for AniVault pipeline.

This module provides the ParallelDirectoryScanner class that uses ThreadPoolExecutor
to perform concurrent directory traversal, significantly improving scan performance
for large directory structures.
"""

from __future__ import annotations

import logging
import os
import threading
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path

from anivault.core.pipeline.utils import BoundedQueue, ScanStatistics
from anivault.shared.errors import ErrorCode, ErrorContext, InfrastructureError
from anivault.shared.logging import log_operation_error, log_operation_success

logger = logging.getLogger(__name__)


class ParallelDirectoryScanner(threading.Thread):
    """Parallel directory scanner using ThreadPoolExecutor.

    This class uses multiple threads to concurrently scan directories,
    significantly improving performance for large directory structures.

    Args:
        root_path: Root directory path to scan.
        extensions: List of file extensions to include (e.g., ['.mp4', '.mkv']).
        input_queue: BoundedQueue instance to put scanned file paths into.
        stats: ScanStatistics instance for tracking scan metrics.
        max_workers: Maximum number of worker threads (default: os.cpu_count() * 2).
        chunk_size: Number of directories to process per worker (default: 10).
    """

    def __init__(
        self,
        root_path: str | Path,
        extensions: list[str],
        input_queue: BoundedQueue,
        stats: ScanStatistics,
        max_workers: int | None = None,
        chunk_size: int = 10,
    ) -> None:
        """Initialize the parallel directory scanner.

        Args:
            root_path: Root directory path to scan.
            extensions: List of file extensions to include.
            input_queue: BoundedQueue instance to put scanned file paths into.
            stats: ScanStatistics instance for tracking scan metrics.
            max_workers: Maximum number of worker threads.
            chunk_size: Number of directories to process per worker.
        """
        super().__init__()
        self.root_path = Path(root_path)
        self.extensions = {ext.lower() for ext in extensions}
        self.input_queue = input_queue
        self.stats = stats
        self.max_workers = max_workers or (os.cpu_count() or 1) * 2
        self.chunk_size = chunk_size
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def _recursive_scan_directory(self, directory: Path) -> tuple[list[Path], int]:
        """Recursively scan a directory using os.scandir for better performance.

        Args:
            directory: Directory path to scan.

        Returns:
            Tuple of (list of file paths found, number of directories scanned).
        """
        found_files = []
        directories_scanned = 0

        try:
            if not directory.exists() or not directory.is_dir():
                return found_files, directories_scanned

            # Use os.scandir for better performance
            with os.scandir(directory) as entries:
                for entry in entries:
                    if self._stop_event.is_set():
                        break

                    try:
                        if entry.is_dir():
                            # Recursively scan subdirectories
                            subdir_files, subdir_count = self._recursive_scan_directory(
                                Path(entry.path),
                            )
                            found_files.extend(subdir_files)
                            directories_scanned += subdir_count
                        elif entry.is_file():
                            # Check if file has one of the specified extensions
                            if entry.path.lower().endswith(tuple(self.extensions)):
                                found_files.append(Path(entry.path).absolute())

                    except (OSError, PermissionError):
                        # Skip inaccessible entries
                        continue

            # Count this directory
            directories_scanned += 1

        except (OSError, PermissionError) as e:
            # Log permission errors but continue scanning
            print(f"Warning: Cannot scan directory {directory}: {e}")

        return found_files, directories_scanned

    def _scan_root_directories(self) -> list[Path]:
        """Get immediate subdirectories of the root for parallel processing.

        Returns:
            List of immediate subdirectory paths.
        """
        subdirectories = []

        try:
            if not self.root_path.exists() or not self.root_path.is_dir():
                return subdirectories

            # Get immediate subdirectories
            with os.scandir(self.root_path) as entries:
                for entry in entries:
                    if self._stop_event.is_set():
                        break

                    try:
                        if entry.is_dir():
                            subdirectories.append(Path(entry.path))
                    except (OSError, PermissionError):
                        continue

        except (OSError, PermissionError) as e:
            print(f"Warning: Error accessing root directory: {e}")

        return subdirectories

    def _thread_safe_put_files(self, file_paths: list[Path]) -> int:
        """Thread-safe method to put multiple files into the queue.

        Args:
            file_paths: List of file paths to queue.

        Returns:
            Number of files successfully queued.
        """
        queued_count = 0

        for file_path in file_paths:
            if self._stop_event.is_set():
                break

            try:
                self.input_queue.put(file_path, timeout=1.0)
                queued_count += 1
            except Exception as e:
                print(f"Warning: Failed to queue file {file_path}: {e}")
                continue

        return queued_count

    def _thread_safe_update_stats(
        self,
        files_count: int,
        directories_count: int,
    ) -> None:
        """Thread-safe method to update scan statistics.

        Args:
            files_count: Number of files processed.
            directories_count: Number of directories processed.
        """
        with self._lock:
            for _ in range(files_count):
                self.stats.increment_files_scanned()
            for _ in range(directories_count):
                self.stats.increment_directories_scanned()

    def _submit_scan_jobs(
        self,
        executor: ThreadPoolExecutor,
        subdirectories: list[Path],
    ) -> dict[Future, Path]:
        """Submit scan jobs for given subdirectories to the executor.

        Args:
            executor: ThreadPoolExecutor instance to submit jobs to.
            subdirectories: List of subdirectory paths to scan.

        Returns:
            Dictionary mapping futures to their corresponding subdirectory paths.

        Raises:
            InfrastructureError: If job submission fails.
        """
        context = ErrorContext(
            operation="submit_scan_jobs",
            additional_data={
                "subdirectories_count": len(subdirectories),
                "max_workers": self.max_workers,
            },
        )

        try:
            future_to_dir = {}

            for subdir in subdirectories:
                if self._stop_event.is_set():
                    break

                try:
                    future = executor.submit(self._recursive_scan_directory, subdir)
                    future_to_dir[future] = subdir

                except RuntimeError as e:
                    log_operation_error(
                        operation="submit_scan_jobs",
                        error=e,
                        context=context,
                        logger=logger,
                    )
                    raise InfrastructureError(
                        ErrorCode.WORKER_POOL_ERROR,
                        f"Failed to submit scan job for directory {subdir}: {e}",
                        context,
                        original_error=e,
                    ) from e

            log_operation_success(
                logger=logger,
                operation="submit_scan_jobs",
                duration_ms=0.0,  # Job submission is very fast
                context=context.additional_data,
            )

            return future_to_dir

        except Exception as e:
            error = InfrastructureError(
                ErrorCode.WORKER_POOL_ERROR,
                f"Failed to submit scan jobs: {e}",
                context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                error=error,
                operation="submit_scan_jobs",
                additional_context=context.additional_data,
            )
            raise error from e

    def _await_scan_completion(self, future_to_dir: dict[Future, Path]) -> None:
        """Wait for scan completion and process results.

        Args:
            future_to_dir: Dictionary mapping futures to their subdirectory paths.
        """
        context = ErrorContext(
            operation="await_scan_completion",
            additional_data={"futures_count": len(future_to_dir)},
        )

        try:
            # Process completed subdirectory futures
            for future in as_completed(future_to_dir):
                if self._stop_event.is_set():
                    # Cancel remaining futures
                    for f in future_to_dir:
                        f.cancel()
                    break

                try:
                    # Check for exceptions from individual jobs
                    if future.exception():
                        subdir = future_to_dir[future]
                        error_context = ErrorContext(
                            operation="individual_scan_job",
                            additional_data={"subdirectory": str(subdir)},
                        )

                        error = InfrastructureError(
                            ErrorCode.SCANNER_ERROR,
                            f"Individual scan job failed for directory {subdir}: {future.exception()}",
                            error_context,
                            original_error=future.exception(),
                        )
                        log_operation_error(
                            logger=logger,
                            error=error,
                            operation="individual_scan_job",
                            additional_context=error_context.additional_data,
                        )
                        continue

                    # Get results from this subdirectory
                    found_files, dirs_scanned = future.result()

                    # Put files into the input queue (thread-safe)
                    queued_files = self._thread_safe_put_files(found_files)

                    # Update statistics (thread-safe)
                    self._thread_safe_update_stats(queued_files, dirs_scanned)

                except Exception as e:
                    subdir = future_to_dir[future]
                    error_context = ErrorContext(
                        operation="process_scan_result",
                        additional_data={"subdirectory": str(subdir)},
                    )

                    error = InfrastructureError(
                        ErrorCode.SCANNER_ERROR,
                        f"Failed to process scan result for directory {subdir}: {e}",
                        error_context,
                        original_error=e,
                    )
                    log_operation_error(
                        logger=logger,
                        error=error,
                        operation="process_scan_result",
                        additional_context=error_context.additional_data,
                    )
                    continue

            log_operation_success(
                logger=logger,
                operation="await_scan_completion",
                duration_ms=0.0,  # Completion time varies
                context=context.additional_data,
            )

        except Exception as e:
            error = InfrastructureError(
                ErrorCode.SCANNER_ERROR,
                f"Failed to await scan completion: {e}",
                context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                error=error,
                operation="await_scan_completion",
                additional_context=context.additional_data,
            )

    def stop(self) -> None:
        """Signal the scanner thread to stop."""
        self._stop_event.set()

    def _scan_subdirectories(self, subdirectories: list[Path]) -> None:
        """Scan subdirectories using ThreadPoolExecutor.

        Args:
            subdirectories: List of subdirectory paths to scan.
        """
        context = ErrorContext(
            operation="scan_subdirectories",
            additional_data={
                "subdirectories_count": len(subdirectories),
                "max_workers": self.max_workers,
            },
        )

        try:
            # Use ThreadPoolExecutor for parallel directory scanning
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit subdirectory scanning tasks
                future_to_dir = self._submit_scan_jobs(executor, subdirectories)

                # Wait for completion and process results
                self._await_scan_completion(future_to_dir)

            log_operation_success(
                logger=logger,
                operation="scan_subdirectories",
                duration_ms=0.0,  # Scanning time varies
                context=context.additional_data,
            )

        except Exception as e:
            error = InfrastructureError(
                ErrorCode.SCANNER_ERROR,
                f"Failed to scan subdirectories: {e}",
                context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                error=error,
                operation="scan_subdirectories",
                additional_context=context.additional_data,
            )

    def run(self) -> None:
        """Main method that orchestrates the parallel scanning process."""
        try:
            # Validate root path
            if not self.root_path.exists():
                print(f"Warning: Root path does not exist: {self.root_path}")
                return

            if not self.root_path.is_dir():
                print(f"Warning: Root path is not a directory: {self.root_path}")
                return

            # Get immediate subdirectories for parallel processing
            subdirectories = self._scan_root_directories()

            # Also scan the root directory itself for files
            root_files = self._scan_root_files()

            print(
                f"Parallel scanning {len(subdirectories)} subdirectories "
                f"using {self.max_workers} workers",
            )

            # Process root files first (thread-safe)
            queued_root_files = self._thread_safe_put_files(root_files)
            self._thread_safe_update_stats(
                queued_root_files,
                1,
            )  # Root directory counted

            # Scan subdirectories using the new method
            self._scan_subdirectories(subdirectories)

        except Exception as e:
            print(f"Error in parallel directory scanning: {e}")
        finally:
            # Signal completion with sentinel
            try:
                self.input_queue.put(None, timeout=1.0)
            except Exception as e:
                print(f"Warning: Failed to put sentinel value: {e}")

    def _scan_root_files(self) -> list[Path]:
        """Scan the root directory for files directly.

        Returns:
            List of file paths found in the root directory.
        """
        root_files = []

        try:
            if not self.root_path.exists() or not self.root_path.is_dir():
                return root_files

            # Scan root directory for files
            with os.scandir(self.root_path) as entries:
                for entry in entries:
                    if self._stop_event.is_set():
                        break

                    try:
                        if entry.is_file():
                            # Check if file has one of the specified extensions
                            if entry.path.lower().endswith(tuple(self.extensions)):
                                root_files.append(Path(entry.path).absolute())

                    except (OSError, PermissionError):
                        continue

            # Root directory will be counted in the main run method

        except (OSError, PermissionError) as e:
            print(f"Warning: Cannot scan root directory: {e}")

        return root_files
