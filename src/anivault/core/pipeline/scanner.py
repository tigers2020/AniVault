"""Directory scanner for AniVault pipeline.

This module provides the DirectoryScanner class that acts as a producer
in the file processing pipeline, scanning directories for files with
specific extensions and feeding them into a bounded queue.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Generator
from pathlib import Path

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
    ) -> None:
        """Initialize the directory scanner.

        Args:
            root_path: Root directory path to scan.
            extensions: List of file extensions to include (e.g., ['.mp4', '.mkv']).
            input_queue: BoundedQueue instance to put scanned file paths into.
            stats: ScanStatistics instance for tracking scan metrics.
        """
        super().__init__()
        self.root_path = Path(root_path)
        self.extensions = {ext.lower() for ext in extensions}
        self.input_queue = input_queue
        self.stats = stats
        self._stop_event = threading.Event()

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
        for root, _dirs, files in os.walk(self.root_path):
            # Convert root to Path for easier manipulation
            root_path = Path(root)

            # Update directory statistics
            self.stats.increment_directories_scanned()

            for file in files:
                file_path = root_path / file

                # Check if file has one of the specified extensions
                if file_path.suffix.lower() in self.extensions:
                    yield file_path.absolute()

    def stop(self) -> None:
        """Signal the scanner thread to stop."""
        self._stop_event.set()

    def run(self) -> None:
        """Main method that orchestrates the scanning process.

        This method scans the directory, puts file paths into the input queue,
        and signals completion with a sentinel value.
        """
        try:
            # Validate root path
            if not self.root_path.exists():
                print(f"Warning: Root path does not exist: {self.root_path}")
                return

            if not self.root_path.is_dir():
                print(f"Warning: Root path is not a directory: {self.root_path}")
                return

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

        except Exception as e:
            print(f"Error during directory scanning: {e}")

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
