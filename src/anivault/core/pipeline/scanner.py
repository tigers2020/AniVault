"""Directory scanner for AniVault pipeline.

This module provides the DirectoryScanner class that acts as a producer
in the file processing pipeline, scanning directories for files with
specific extensions and feeding them into a bounded queue.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from anivault.core.filter import FilterEngine
from anivault.core.pipeline.utils import BoundedQueue, ScanStatistics


class DirectoryScanner(threading.Thread):
    """Directory scanner that acts as a producer in the pipeline.

    This class recursively scans a directory for files with specific
    extensions and feeds them into a bounded queue for processing.

    Args:
        root_path: Root directory path to scan.
        extensions: List of file extensions to include (e.g., ['.mp4', '.mkv']).
        input_queue: BoundedQueue instance to put scanned file paths into.
        stats: ScanStatistics instance for tracking scan metrics.
    """

    def __init__(
        self,
        root_path: str | Path,
        extensions: list[str],
        input_queue: BoundedQueue,
        stats: ScanStatistics,
        parallel: bool = False,
        max_workers: int | None = None,
        quiet: bool = False,
        filter_engine: FilterEngine | None = None,
        batch_size: int = 100,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> None:
        """Initialize the directory scanner.

        Args:
            root_path: Root directory path to scan.
            extensions: List of file extensions to include (e.g., ['.mp4', '.mkv']).
            input_queue: BoundedQueue instance to put scanned file paths into.
            stats: ScanStatistics instance for tracking scan metrics.
            parallel: Whether to use parallel scanning with ThreadPoolExecutor.
            max_workers: Maximum number of worker threads for parallel scanning.
            quiet: Whether to suppress adaptive threshold messages.
            filter_engine: Optional FilterEngine instance for smart filtering.
            batch_size: Number of files to include in each batch when using generator API.
            progress_callback: Optional callback function to report scan progress.
                              Called with a dict containing progress information.
            cancel_event: Optional threading.Event to signal scan cancellation.
                         If provided, overrides the internal _stop_event.
        """
        super().__init__()
        self.root_path = Path(root_path)
        self.extensions = {ext.lower() for ext in extensions}
        self.input_queue = input_queue
        self.stats = stats
        self.parallel = parallel
        self.max_workers = max_workers or (os.cpu_count() or 1) * 2
        self._stop_event = (
            cancel_event if cancel_event is not None else threading.Event()
        )
        self._lock = threading.Lock()
        self._quiet_mode = quiet
        # Adaptive threshold for parallel processing
        self.parallel_threshold = (
            1000  # Minimum files to benefit from parallel processing
        )
        self.filter_engine = filter_engine
        self.batch_size = batch_size
        self.progress_callback = progress_callback

    def _report_progress(self, **kwargs: Any) -> None:
        """
        Report progress to the callback if one is registered.

        Args:
            **kwargs: Progress data to report (e.g., files_scanned, dirs_scanned, etc.)
        """
        if self.progress_callback:
            try:
                self.progress_callback(kwargs)
            except Exception:
                # Silently ignore callback errors to prevent scan interruption
                pass

    def scan_files(self) -> Generator[Path, None, None]:
        """Generator that recursively scans for files with specified extensions.

        Yields:
            Path: Absolute path of each file that matches the specified extensions.
        """
        if not self.root_path.exists():
            return

        if not self.root_path.is_dir():
            return

        # Use os.walk for efficient directory traversal
        for root, dirs, files in os.walk(self.root_path):
            # Convert root to Path for easier manipulation
            root_path = Path(root)

            # Apply directory filtering if FilterEngine is available
            if self.filter_engine:
                # Filter out excluded directories in-place to prevent os.walk from traversing them
                dirs[:] = [
                    d for d in dirs if not self.filter_engine.should_skip_directory(d)
                ]

            # Update directory statistics
            self.stats.increment_directories_scanned()

            for file in files:
                file_path = root_path / file

                # Check if file has one of the specified extensions
                if file_path.suffix.lower() in self.extensions:
                    # Apply file filtering if FilterEngine is available
                    if self.filter_engine:
                        try:
                            # Get file stats for filtering
                            file_stat = file_path.stat()
                            if self.filter_engine.should_skip_file(
                                file_path,
                                file_stat,
                            ):
                                continue  # Skip this file
                        except (OSError, PermissionError):
                            # Skip files we can't stat
                            continue

                    yield file_path.absolute()

    def scan(self) -> Generator[list[Path], None, None]:
        """
        Scan directory and yield batches of file paths as they are discovered.

        This method provides a generator-based API for streaming file discovery,
        enabling memory-efficient processing of large directory structures by
        yielding files in configurable batches rather than individually.

        Yields:
            list[Path]: Batch of file paths that match the specified extensions
                       and pass filtering criteria. Each batch contains up to
                       batch_size files.
        """
        if not self.root_path.exists():
            return

        if not self.root_path.is_dir():
            return

        # Collect files into batches
        current_batch = []
        batch_count = 0

        for file_path in self.scan_files():
            current_batch.append(file_path)

            # Yield batch when it reaches the desired size
            if len(current_batch) >= self.batch_size:
                yield current_batch.copy()
                current_batch.clear()
                batch_count += 1

                # Periodic garbage collection hint every 10 batches
                if batch_count % 10 == 0:
                    import gc

                    gc.collect()  # Suggest garbage collection

        # Yield remaining files in the final batch
        if current_batch:
            yield current_batch

    def scan_with_backpressure(
        self,
        output_queue: BoundedQueue,
    ) -> Generator[list[Path], None, None]:
        """
        Scan directory and yield batches of file paths with backpressure control.

        This method provides a generator-based API for streaming file discovery
        with integrated backpressure management. When the output queue is full,
        scanning pauses until space becomes available, preventing memory overflow.

        Args:
            output_queue: BoundedQueue to monitor for backpressure control.

        Yields:
            list[Path]: Batch of file paths that match the specified extensions
                       and pass filtering criteria. Each batch contains up to
                       batch_size files.
        """
        if not self.root_path.exists():
            return

        if not self.root_path.is_dir():
            return

        # Collect files into batches
        current_batch = []
        batch_count = 0

        for file_path in self.scan_files():
            current_batch.append(file_path)

            # Check for backpressure when batch is full
            if len(current_batch) >= self.batch_size:
                # Check if queue has space (non-blocking check)
                queue_usage = output_queue.qsize() / output_queue.maxsize
                if queue_usage >= 0.8:  # 80% threshold
                    # Yield batch but indicate backpressure
                    yield current_batch.copy()
                    current_batch.clear()
                    batch_count += 1
                    # Small pause to allow queue processing
                    import time

                    time.sleep(0.01)
                else:
                    yield current_batch.copy()
                    current_batch.clear()
                    batch_count += 1

                # Periodic garbage collection hint every 10 batches
                if batch_count % 10 == 0:
                    import gc

                    gc.collect()  # Suggest garbage collection

        # Yield remaining files in the final batch
        if current_batch:
            yield current_batch

    def _parallel_scan_directory(self, directory: Path) -> tuple[list[Path], int]:
        """Recursively scan a directory using os.scandir for parallel processing.

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
                            # Apply directory filtering if FilterEngine is available
                            if (
                                self.filter_engine
                                and self.filter_engine.should_skip_directory(entry.name)
                            ):
                                continue  # Skip this directory

                            # Recursively scan subdirectories
                            subdir_files, subdir_count = self._parallel_scan_directory(
                                Path(entry.path),
                            )
                            found_files.extend(subdir_files)
                            directories_scanned += subdir_count
                        elif entry.is_file():
                            # Check if file has one of the specified extensions
                            if entry.path.lower().endswith(tuple(self.extensions)):
                                file_path = Path(entry.path).absolute()

                                # Apply file filtering if FilterEngine is available
                                if self.filter_engine:
                                    try:
                                        # Get file stats for filtering
                                        file_stat = entry.stat()
                                        if self.filter_engine.should_skip_file(
                                            file_path,
                                            file_stat,
                                        ):
                                            continue  # Skip this file
                                    except (OSError, PermissionError):
                                        # Skip files we can't stat
                                        continue

                                found_files.append(file_path)

                    except (OSError, PermissionError):
                        # Skip inaccessible entries
                        continue

            # Count this directory
            directories_scanned += 1

        except (OSError, PermissionError) as e:
            # Log permission errors but continue scanning
            print(f"Warning: Cannot scan directory {directory}: {e}")

        return found_files, directories_scanned

    def _get_immediate_subdirectories(self) -> list[Path]:
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
                            # Apply directory filtering if FilterEngine is available
                            if (
                                self.filter_engine
                                and self.filter_engine.should_skip_directory(entry.name)
                            ):
                                continue  # Skip this directory
                            subdirectories.append(Path(entry.path))
                    except (OSError, PermissionError):
                        continue

        except (OSError, PermissionError) as e:
            print(f"Warning: Error accessing root directory: {e}")

        return subdirectories

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
                                file_path = Path(entry.path).absolute()

                                # Apply file filtering if FilterEngine is available
                                if self.filter_engine:
                                    try:
                                        # Get file stats for filtering
                                        file_stat = entry.stat()
                                        if self.filter_engine.should_skip_file(
                                            file_path,
                                            file_stat,
                                        ):
                                            continue  # Skip this file
                                    except (OSError, PermissionError):
                                        # Skip files we can't stat
                                        continue

                                root_files.append(file_path)

                    except (OSError, PermissionError):
                        continue

        except (OSError, PermissionError) as e:
            print(f"Warning: Cannot scan root directory: {e}")

        return root_files

    def _estimate_total_files(self) -> int:
        """Estimate the total number of files to be scanned.

        Returns:
            Estimated number of files matching the extensions.
        """
        try:
            file_count = 0
            for _root, _dirs, files in os.walk(self.root_path):
                for file in files:
                    if Path(file).suffix.lower() in self.extensions:
                        file_count += 1
                # Early termination if we have enough samples
                if file_count > self.parallel_threshold * 2:
                    break
            return file_count
        except (OSError, PermissionError):
            return 0

    def _should_use_parallel(self) -> bool:
        """Determine if parallel processing should be used based on adaptive threshold.

        Returns:
            True if parallel processing is recommended, False otherwise.
        """
        if not self.parallel:
            return False

        # Estimate total files to determine if parallel processing is beneficial
        estimated_files = self._estimate_total_files()
        should_use_parallel = estimated_files >= self.parallel_threshold

        if not should_use_parallel and not getattr(self, "_quiet_mode", False):
            print(
                f"Adaptive threshold: Sequential scanning recommended for {estimated_files} files "
                f"(threshold: {self.parallel_threshold})",
            )

        return should_use_parallel

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

    def stop(self) -> None:
        """Signal the scanner thread to stop."""
        self._stop_event.set()

    def run(self) -> None:
        """Main method that orchestrates the scanning process.

        This method scans the directory using either sequential or parallel processing,
        puts file paths into the input queue, and signals completion with a sentinel value.
        """
        try:
            # Validate root path
            if not self.root_path.exists():
                print(f"Warning: Root path does not exist: {self.root_path}")
                return

            if not self.root_path.is_dir():
                print(f"Warning: Root path is not a directory: {self.root_path}")
                return

            # Use adaptive threshold to determine if parallel processing is beneficial
            if self._should_use_parallel():
                self._run_parallel_scan()
            else:
                self._run_sequential_scan()

        except Exception as e:
            print(f"Error during directory scanning: {e}")
        finally:
            # Signal completion with sentinel
            try:
                self.input_queue.put(None, timeout=1.0)
            except Exception as e:
                print(f"Warning: Failed to put sentinel value: {e}")

    def _run_sequential_scan(self) -> None:
        """Run sequential directory scanning using the original method."""
        # Scan files and put them into the queue
        for file_path in self.scan_files():
            # Check if we should stop
            if self._stop_event.is_set():
                break

            try:
                self.input_queue.put(file_path)
                self.stats.increment_files_scanned()
            except Exception as e:
                print(f"Error putting file {file_path} into queue: {e}")
                continue

    def _run_parallel_scan(self) -> None:
        """Run parallel directory scanning using ThreadPoolExecutor."""
        # Get immediate subdirectories for parallel processing
        subdirectories = self._get_immediate_subdirectories()

        # Also scan the root directory itself for files
        root_files = self._scan_root_files()

        print(
            f"Parallel scanning {len(subdirectories)} subdirectories "
            f"using {self.max_workers} workers",
        )

        # Use ThreadPoolExecutor for parallel directory scanning
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit subdirectory scanning tasks
            future_to_dir = {}
            for subdir in subdirectories:
                if self._stop_event.is_set():
                    break
                future = executor.submit(self._parallel_scan_directory, subdir)
                future_to_dir[future] = subdir

            # Process root files first (thread-safe)
            queued_root_files = self._thread_safe_put_files(root_files)
            self._thread_safe_update_stats(
                queued_root_files,
                1,
            )  # Root directory counted

            # Process completed subdirectory futures
            for future in as_completed(future_to_dir):
                if self._stop_event.is_set():
                    # Cancel remaining futures
                    for f in future_to_dir:
                        f.cancel()
                    break

                try:
                    # Get results from this subdirectory
                    found_files, dirs_scanned = future.result()

                    # Put files into the input queue (thread-safe)
                    queued_files = self._thread_safe_put_files(found_files)

                    # Update statistics (thread-safe)
                    self._thread_safe_update_stats(queued_files, dirs_scanned)

                except Exception as e:
                    subdir = future_to_dir[future]
                    print(f"Error processing subdirectory {subdir}: {e}")
                    continue

    def get_scan_summary(self) -> dict:
        """Get a summary of the scanning results.

        Returns:
            Dictionary containing scan statistics and information.
        """
        return {
            "root_path": str(self.root_path),
            "extensions": list(self.extensions),
            "files_scanned": self.stats.files_scanned,
            "directories_scanned": self.stats.directories_scanned,
            "queue_size": self.input_queue.qsize(),
            "queue_maxsize": self.input_queue.maxsize,
        }
