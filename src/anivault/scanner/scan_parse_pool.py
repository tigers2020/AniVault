"""ScanParsePool module for AniVault.

This module provides the core file processing pipeline using ThreadPoolExecutor
for parallel scanning and parsing operations.
"""

from collections.abc import Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Optional

from anivault.core.logging import get_logger
from anivault.scanner.extension_filter import get_default_media_filter
from anivault.scanner.parser_worker import ParserWorkerPool
from anivault.scanner.producer_scanner import Scanner

logger = get_logger(__name__)
import queue


class ScanParsePool:
    """Main file processing pipeline using ThreadPoolExecutor with bounded queues.

    This class manages a thread pool for parallel file processing, including
    directory scanning and file parsing operations. It uses bounded queues to
    manage memory and prevent overflow between the scanner (producer) and
    parser (consumer) stages.

    Attributes:
        max_workers: Maximum number of worker threads in the pool.
        extension_filter: Function to filter files by extension.
        parse_function: Function to parse individual files.
        queue_size: Maximum size of the bounded queue.
    """

    def __init__(
        self,
        max_workers: Optional[int] = None,
        extension_filter: Optional[Callable[[str], bool]] = None,
        parse_function: Optional[Callable[[str], Any]] = None,
        queue_size: int = 1000,
    ) -> None:
        """Initialize the ScanParsePool.

        Args:
            max_workers: Maximum number of worker threads. If None, uses
                min(32, (os.cpu_count() or 1) + 4) as per ThreadPoolExecutor default.
            extension_filter: Optional function to filter files by extension.
                If None, uses default media file filter.
            parse_function: Optional function to parse individual files.
                If None, files are just yielded without parsing.
            queue_size: Maximum size of the bounded queue for backpressure.
        """
        self.max_workers = max_workers
        # Use default media filter if no extension filter provided
        self.extension_filter = extension_filter or get_default_media_filter()
        self.parse_function = parse_function
        self.queue_size = queue_size

        # Initialize thread pool executor
        self._executor: Optional[ThreadPoolExecutor] = None

        # Initialize bounded queue for producer-consumer pattern
        self._file_queue: Optional[queue.Queue[Any]] = None

        # Initialize scanner (producer)
        self._scanner: Optional[Scanner] = None

        # Initialize parser worker pool (consumer)
        self._parser_pool: Optional[ParserWorkerPool] = None

        # Statistics tracking
        self._stats = {
            "files_scanned": 0,
            "files_queued": 0,
            "files_processed": 0,
            "queue_put_blocks": 0,
            "queue_get_blocks": 0,
        }

        logger.info(
            f"Initialized ScanParsePool with max_workers={max_workers}, "
            f"extension_filter={'custom' if extension_filter else 'default media'}, "
            f"parse_function={parse_function is not None}, "
            f"queue_size={queue_size}",
        )

    def __enter__(self) -> "ScanParsePool":
        """Context manager entry.

        Returns:
            Self for use in 'with' statements.
        """
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit.

        Args:
            exc_type: Exception type if any.
            exc_val: Exception value if any.
            exc_tb: Exception traceback if any.
        """
        self.shutdown()

    def start(self) -> None:
        """Start the thread pool executor and initialize the bounded queue."""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
            self._file_queue = queue.Queue(maxsize=self.queue_size)
            self._scanner = Scanner(extension_filter=self.extension_filter)

            # Initialize parser worker pool if parse function is provided
            if self.parse_function is not None:
                self._parser_pool = ParserWorkerPool(
                    parse_function=self.parse_function,
                    max_workers=self.max_workers,
                )
                self._parser_pool.start()

            logger.info(
                f"Started ThreadPoolExecutor with {self.max_workers} workers and queue size {self.queue_size}",
            )
        else:
            logger.warning("ThreadPoolExecutor already started")

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the thread pool executor.

        Args:
            wait: Whether to wait for all tasks to complete before shutdown.
        """
        if self._executor is not None:
            # Signal end of queue by putting None
            if self._file_queue is not None:
                try:
                    self._file_queue.put(None, timeout=1)
                except queue.Full:
                    pass

            # Shutdown parser worker pool
            if self._parser_pool is not None:
                self._parser_pool.shutdown(wait=wait)

            self._executor.shutdown(wait=wait)
            logger.info(f"Shutdown ThreadPoolExecutor (wait={wait})")
            self._executor = None
            self._file_queue = None
            self._scanner = None
            self._parser_pool = None

    def is_running(self) -> bool:
        """Check if the thread pool is running.

        Returns:
            True if the thread pool is active, False otherwise.
        """
        return self._executor is not None

    def submit_scan_task(self, directory_path: str | Path) -> Future[None]:
        """Submit a directory scanning task to the thread pool.

        Args:
            directory_path: Path to the directory to scan.

        Returns:
            Future object representing the scanning task.

        Raises:
            RuntimeError: If the thread pool is not started.
        """
        if self._executor is None:
            raise RuntimeError("ThreadPoolExecutor not started. Call start() first.")

        if self._scanner is None:
            raise RuntimeError("Scanner not initialized. Call start() first.")

        future = self._executor.submit(
            self._scanner.scan,
            directory_path,
            self._file_queue,
            self.max_workers,
        )
        logger.debug(f"Submitted scan task for directory: {directory_path}")
        return future

    def submit_parse_task(self, file_path: str) -> Future[Any]:
        """Submit a file parsing task to the thread pool.

        Args:
            file_path: Path to the file to parse.

        Returns:
            Future object representing the parsing task.

        Raises:
            RuntimeError: If the thread pool is not started or parse function not set.
        """
        if self._executor is None:
            raise RuntimeError("ThreadPoolExecutor not started. Call start() first.")

        if self.parse_function is None:
            raise RuntimeError("Parse function not set. Cannot submit parse task.")

        future = self._executor.submit(self.parse_function, file_path)
        logger.debug(f"Submitted parse task for file: {file_path}")
        return future

    def _consume_queue(self) -> Iterator[str]:
        """Consume files from the bounded queue.

        Yields:
            File paths from the queue.
        """
        if self._file_queue is None:
            raise RuntimeError("Queue not initialized. Call start() first.")

        while True:
            try:
                file_path = self._file_queue.get(timeout=1)
                if file_path is None:  # End signal
                    break

                self._stats["files_processed"] += 1
                yield file_path
                self._file_queue.task_done()

            except queue.Empty:
                # No items in queue, continue waiting
                continue
            except Exception as e:
                logger.error(f"Error consuming from queue: {e}")
                break

    def process_directory(self, directory_path: str | Path) -> Iterator[Any]:
        """Process a directory by scanning and optionally parsing files.

        This method scans the directory and yields results. If a parse function
        is set, it submits parse tasks for each file and yields the results.

        Args:
            directory_path: Path to the directory to process.

        Yields:
            File paths or parsed results depending on whether parse function is set.
        """
        if self._executor is None:
            raise RuntimeError("ThreadPoolExecutor not started. Call start() first.")

        # Start scanning task
        scan_future = self.submit_scan_task(directory_path)

        if self.parse_function is None:
            # Just yield file paths from queue
            for file_path in self._consume_queue():
                yield file_path
        else:
            # Use parser worker pool for parallel processing
            if self._parser_pool is None:
                raise RuntimeError("Parser worker pool not initialized.")

            # Submit consume tasks to parser workers
            consume_futures = self._parser_pool.submit_consume_task(self._file_queue)

            # Collect results as they complete
            for future in consume_futures:
                try:
                    results = future.result()
                    for result in results:
                        yield result
                except Exception as e:
                    logger.error(f"Error in parser worker: {e}")
                    continue

        # Wait for scan task to complete
        try:
            scan_future.result()
        except Exception as e:
            logger.error(f"Error in scan task: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the thread pool and queue.

        Returns:
            Dictionary containing thread pool and queue statistics.
        """
        stats = {
            "is_running": self.is_running(),
            "max_workers": self.max_workers,
            "queue_size": self.queue_size,
            "has_extension_filter": self.extension_filter is not None,
            "has_parse_function": self.parse_function is not None,
            **self._stats,
        }

        if self._executor is not None:
            stats.update(
                {
                    "_threads": len(self._executor._threads)
                    if hasattr(self._executor, "_threads")
                    else None,
                    "_work_queue_size": self._executor._work_queue.qsize()
                    if hasattr(self._executor, "_work_queue")
                    else None,
                },
            )

        if self._file_queue is not None:
            stats.update(
                {
                    "queue_current_size": self._file_queue.qsize(),
                    "queue_maxsize": self._file_queue.maxsize,
                },
            )

        # Add scanner stats if available
        if self._scanner is not None:
            stats.update(
                {
                    "scanner_stats": self._scanner.get_stats(),
                },
            )

        # Add parser pool stats if available
        if self._parser_pool is not None:
            stats.update(
                {
                    "parser_pool_stats": self._parser_pool.get_stats(),
                },
            )

        return stats
