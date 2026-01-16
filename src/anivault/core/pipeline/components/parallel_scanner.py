"""Parallel directory scanner for AniVault pipeline.

This module provides the ParallelDirectoryScanner class that uses ThreadPoolExecutor
to perform concurrent directory traversal, significantly improving scan performance
for large directory structures.
"""

from __future__ import annotations

import logging
import os
import threading
from concurrent.futures import (
    CancelledError,
    Future,
    ThreadPoolExecutor,
    as_completed,
)
from concurrent.futures import TimeoutError as FutureTimeoutError
from pathlib import Path

from anivault.config import load_settings
from anivault.core.pipeline.utils import BoundedQueue, ScanStatistics
from anivault.shared.constants import ProcessingConfig
from anivault.shared.constants.network import NetworkConfig
from anivault.shared.errors import (
    ErrorCode,
    ErrorContextModel,
    InfrastructureError,
)
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

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        root_path: str | Path,
        extensions: list[str],
        input_queue: BoundedQueue,
        stats: ScanStatistics,
        max_workers: int | None = None,
        chunk_size: int = ProcessingConfig.DEFAULT_BATCH_SIZE,
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
        # Use optimized worker count: min(32, (cpu_count or 4) + 4)
        self.max_workers = max_workers or min(32, (os.cpu_count() or 4) + 4)
        self.chunk_size = chunk_size
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        # Use common synchronization utility for stats updates
        from anivault.core.pipeline.utils.synchronization import ThreadSafeStatsUpdater

        self._stats_updater = ThreadSafeStatsUpdater(stats, self._lock)

    def _get_parallel_threshold(self) -> int:
        """Get parallel_threshold from configuration.

        Returns:
            Minimum directory count to use parallel scanning (default: 5)
        """
        try:
            settings = load_settings()
            if hasattr(settings, "scan") and settings.scan is not None:
                threshold = settings.scan.parallel_threshold
                # Use threshold as-is, but ensure minimum of 5 for directory count
                return max(5, threshold // 100)  # Scale down from file count threshold
        except (ImportError, AttributeError) as e:
            logger.debug(
                "Could not load parallel_threshold from config, using default 5: %s",
                e,
            )

        # Default to 5 directories for sequential mode
        return 5

    def _recursive_scan_directory(self, directory: Path) -> tuple[list[Path], int]:
        """Recursively scan a directory using os.scandir for better performance.

        Args:
            directory: Directory path to scan.

        Returns:
            Tuple of (list of file paths found, number of directories scanned).
        """
        found_files: list[Path] = []
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

        except (OSError, PermissionError):
            # Log permission errors but continue scanning
            logger.warning("Cannot scan directory: %s", directory, exc_info=True)

        return found_files, directories_scanned

    def _scan_root_directories(self) -> list[Path]:
        """Get immediate subdirectories of the root for parallel processing.

        Returns:
            List of immediate subdirectory paths.
        """
        subdirectories: list[Path] = []

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

        except (OSError, PermissionError):
            logger.warning("Error accessing root directory", exc_info=True)

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
                self.input_queue.put(file_path, timeout=NetworkConfig.DEFAULT_TIMEOUT)
                queued_count += 1
            except (FutureTimeoutError, OSError) as e:  # pylint: disable=bad-except-order
                # Queue timeout or OS errors
                context = ErrorContextModel(
                    file_path=str(file_path),
                    operation="queue_file_parallel",
                )
                error = InfrastructureError(
                    ErrorCode.QUEUE_OPERATION_ERROR,
                    f"Failed to queue file: {e}",
                    context,
                    original_error=e,
                )
                logger.warning(
                    "Failed to queue file: %s: %s",
                    file_path,
                    error.message,
                    exc_info=True,
                )
                continue

        return queued_count

    def _thread_safe_update_stats(
        self,
        files_count: int,
        directories_count: int,
    ) -> None:
        """Thread-safe method to update scan statistics.

        Uses common synchronization utility for consistency.

        Args:
            files_count: Number of files processed.
            directories_count: Number of directories processed.
        """
        self._stats_updater.update_files_and_directories(files_count, directories_count)

    def _submit_scan_jobs(
        self,
        executor: ThreadPoolExecutor,
        subdirectories: list[Path],
    ) -> dict[Future[tuple[list[Path], int]], Path]:
        """Submit scan jobs for given subdirectories to the executor.

        Args:
            executor: ThreadPoolExecutor instance to submit jobs to.
            subdirectories: List of subdirectory paths to scan.

        Returns:
            Dictionary mapping futures to their corresponding subdirectory paths.

        Raises:
            InfrastructureError: If job submission fails.
        """
        context = ErrorContextModel(
            operation="submit_scan_jobs",
            additional_data={
                "subdirectories_count": len(subdirectories),
                "max_workers": self.max_workers,
            },
        )

        try:
            future_to_dir: dict[Future[tuple[list[Path], int]], Path] = {}

            for subdir in subdirectories:
                if self._stop_event.is_set():
                    break

                try:
                    future = executor.submit(self._recursive_scan_directory, subdir)
                    future_to_dir[future] = subdir

                except (RuntimeError, ValueError, TypeError) as e:
                    error = InfrastructureError(
                        code=ErrorCode.WORKER_POOL_ERROR,
                        message=f"Failed to submit scan jobs: {e!s}",
                        context=context,
                        original_error=e,
                    )
                    log_operation_error(
                        operation="submit_scan_jobs",
                        error=error,
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

        except (RuntimeError, ValueError, TypeError) as e:
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

    def _await_scan_completion(
        self,
        future_to_dir: dict[Future[tuple[list[Path], int]], Path],
    ) -> None:
        """Wait for scan completion and process results.

        Args:
            future_to_dir: Dictionary mapping futures to their subdirectory paths.
        """
        context = ErrorContextModel(
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
                        error_context = ErrorContextModel(
                            operation="individual_scan_job",
                            additional_data={"subdirectory": str(subdir)},
                        )

                        exception = future.exception()
                        error = InfrastructureError(
                            ErrorCode.SCANNER_ERROR,
                            (f"Individual scan job failed for directory {subdir}: {exception}"),
                            error_context,
                            original_error=(exception if isinstance(exception, Exception) else None),
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

                except (
                    CancelledError,
                    FutureTimeoutError,
                    RuntimeError,
                    ValueError,
                ) as e:
                    subdir = future_to_dir[future]
                    error_context = ErrorContextModel(
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

        except (
            CancelledError,
            FutureTimeoutError,
            RuntimeError,
            ValueError,
            TimeoutError,
            OSError,
        ) as e:
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
        context = ErrorContextModel(
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

        except (
            CancelledError,
            FutureTimeoutError,
            RuntimeError,
            ValueError,
            TypeError,
            TimeoutError,
            OSError,
        ) as e:
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
                logger.warning("Root path does not exist: %s", self.root_path)
                return

            if not self.root_path.is_dir():
                logger.warning("Root path is not a directory: %s", self.root_path)
                return

            # Get immediate subdirectories for parallel processing
            subdirectories = self._scan_root_directories()

            # Also scan the root directory itself for files
            root_files = self._scan_root_files()

            # Process root files first (thread-safe)
            queued_root_files = self._thread_safe_put_files(root_files)
            self._thread_safe_update_stats(
                queued_root_files,
                1,
            )  # Root directory counted

            # Get parallel_threshold from configuration
            parallel_threshold = self._get_parallel_threshold()

            # Check if directory count is below threshold for sequential mode
            if len(subdirectories) < parallel_threshold:
                logger.info(
                    "Sequential scanning %d subdirectories (below threshold: %d)",
                    len(subdirectories),
                    parallel_threshold,
                )
                # Sequential mode: scan directories one by one
                for subdir in subdirectories:
                    if self._stop_event.is_set():
                        break
                    found_files, dirs_scanned = self._recursive_scan_directory(subdir)
                    queued_files = self._thread_safe_put_files(found_files)
                    self._thread_safe_update_stats(queued_files, dirs_scanned)
            else:
                logger.info(
                    "Parallel scanning %d subdirectories using %d workers",
                    len(subdirectories),
                    self.max_workers,
                )
                # Scan subdirectories using parallel method
                self._scan_subdirectories(subdirectories)

        except PermissionError as e:
            # Permission errors during parallel scanning
            context = ErrorContextModel(
                file_path=str(self.root_path),
                operation="parallel_directory_scanning",
            )
            error = InfrastructureError(
                ErrorCode.FILE_ACCESS_ERROR,
                f"Permission error in parallel directory scanning: {e}",
                context,
                original_error=e,
            )
            logger.exception("Error in parallel directory scanning: %s", error.message)
        # pylint: disable-next=bad-except-order  # TimeoutError is OSError subclass but must be handled first
        except (TimeoutError, FutureTimeoutError) as e:
            # Timeout errors (OSError subclass, must come before OSError)
            # FutureTimeoutError is an alias for concurrent.futures.TimeoutError
            # which is itself an alias for TimeoutError
            # Note: TimeoutError is a subclass of OSError, but we want to handle
            # timeout errors separately before general OSError handling.
            # This is intentional - we catch TimeoutError first for specific handling.
            context = ErrorContextModel(
                file_path=str(self.root_path),
                operation="parallel_directory_scanning",
            )
            error = InfrastructureError(
                ErrorCode.FILE_ACCESS_ERROR,
                f"Timeout error in parallel directory scanning: {e}",
                context,
                original_error=e,
            )
            logger.exception("Error in parallel directory scanning: %s", error.message)
        except OSError as e:
            # Other OS errors (must come after TimeoutError)
            context = ErrorContextModel(
                file_path=str(self.root_path),
                operation="parallel_directory_scanning",
            )
            error = InfrastructureError(
                ErrorCode.FILE_ACCESS_ERROR,
                f"File system error in parallel directory scanning: {e}",
                context,
                original_error=e,
            )
            logger.exception("Error in parallel directory scanning: %s", error.message)
        except (
            CancelledError,
            RuntimeError,
            ValueError,
            TypeError,
        ) as e:
            # Unexpected errors during parallel scanning
            context = ErrorContextModel(
                file_path=str(self.root_path),
                operation="parallel_directory_scanning",
            )
            error = InfrastructureError(
                ErrorCode.SCANNER_ERROR,
                f"Unexpected error in parallel directory scanning: {e}",
                context,
                original_error=e,
            )
            logger.exception("Error in parallel directory scanning: %s", error.message)
        finally:
            # Signal completion with sentinel
            try:
                self.input_queue.put(None, timeout=NetworkConfig.DEFAULT_TIMEOUT)
            except (FutureTimeoutError, OSError) as e:  # pylint: disable=bad-except-order
                # Queue timeout or OS errors
                context = ErrorContextModel(operation="put_sentinel_parallel")
                error = InfrastructureError(
                    ErrorCode.QUEUE_OPERATION_ERROR,
                    f"Failed to put sentinel value: {e}",
                    context,
                    original_error=e,
                )
                logger.warning("Failed to put sentinel value: %s", error.message, exc_info=True)

    def _scan_root_files(self) -> list[Path]:
        """Scan the root directory for files directly.

        Returns:
            List of file paths found in the root directory.
        """
        root_files: list[Path] = []

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

        except (OSError, PermissionError):
            logger.warning("Cannot scan root directory", exc_info=True)

        return root_files
