"""Parallel directory scanner for AniVault pipeline.

This module provides the ParallelDirectoryScanner class that uses ThreadPoolExecutor
to perform concurrent directory traversal, significantly improving scan performance
for large directory structures.
"""

from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from anivault.core.pipeline.utils import BoundedQueue, ScanStatistics


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

    def stop(self) -> None:
        """Signal the scanner thread to stop."""
        self._stop_event.set()

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

            # Use ThreadPoolExecutor for parallel directory scanning
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit subdirectory scanning tasks
                future_to_dir = {}
                for subdir in subdirectories:
                    if self._stop_event.is_set():
                        break
                    future = executor.submit(self._recursive_scan_directory, subdir)
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
