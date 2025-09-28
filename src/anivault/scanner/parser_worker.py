"""Parser Worker module for AniVault.

This module provides a dedicated ParserWorker class that acts as a consumer,
getting file paths from a bounded queue and processing them with parsing functions.
"""

import queue
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Optional

from anivault.core.logging import get_logger

logger = get_logger(__name__)


class ParserWorker:
    """Consumer worker that processes files from a bounded queue.

    This class acts as a consumer in the producer-consumer pattern,
    getting file paths from a bounded queue and processing them with
    parsing functions.

    Attributes:
        parse_function: Function to parse individual files.
        stats: Dictionary tracking parser statistics.
    """

    def __init__(
        self,
        parse_function: Callable[[str], Any],
    ) -> None:
        """Initialize the ParserWorker.

        Args:
            parse_function: Function to parse individual files.
        """
        self.parse_function = parse_function

        # Statistics tracking
        self.stats = {
            "files_processed": 0,
            "parse_successes": 0,
            "parse_errors": 0,
            "queue_get_blocks": 0,
            "queue_get_errors": 0,
        }

        logger.info(
            f"Initialized ParserWorker with parse_function={getattr(parse_function, '__name__', 'unknown')}",
        )

    def consume_queue(
        self,
        file_queue: queue.Queue[Any],
        timeout: float = 0.2,
    ) -> list[Any]:
        """Consume files from the bounded queue and process them to completion.

        Args:
            file_queue: Bounded queue to get file paths from.
            timeout: Timeout for queue operations.

        Returns:
            List of parsed results from the parse function.
        """
        logger.debug("Starting queue consumption")
        results: list[Any] = []

        while True:
            try:
                file_path = file_queue.get(timeout=timeout)  # 짧게 대기
            except queue.Empty:
                # Nothing right now; keep polling until sentinel arrives
                self.stats["queue_get_blocks"] += 1
                continue
            except Exception as e:
                self.stats["queue_get_errors"] += 1
                logger.error(f"Error getting file from queue: {e}")
                # No task_done here because get() failed
                break

            try:
                # End-of-queue signal
                if file_path is None:
                    logger.debug("Received end-of-queue signal")
                    # IMPORTANT: sentinel corresponds to a put(None); must task_done()
                    file_queue.task_done()
                    break

                self.stats["files_processed"] += 1
                logger.debug(f"Processing file: {file_path}")

                try:
                    result = self.parse_function(file_path)
                    self.stats["parse_successes"] += 1
                    results.append(result)
                    logger.debug(f"Successfully parsed: {file_path}")
                except Exception as e:
                    self.stats["parse_errors"] += 1
                    logger.error(f"Error parsing file {file_path}: {e}")
                finally:
                    file_queue.task_done()

            except Exception as e:
                # If anything above unexpectedly raises before task_done(),
                # make sure we don't swallow a required task_done().
                try:
                    file_queue.task_done()
                except Exception:
                    pass
                logger.exception(f"Unexpected error in consume loop: {e}")
                break

        logger.info(
            f"ParserWorker finished: {self.stats['files_processed']} files processed",
        )
        return results

    def get_stats(self) -> dict[str, Any]:
        """Get parser worker statistics.

        Returns:
            Dictionary containing parser worker statistics.
        """
        return self.stats.copy()

    def reset_stats(self) -> None:
        """Reset parser worker statistics."""
        self.stats = {
            "files_processed": 0,
            "parse_successes": 0,
            "parse_errors": 0,
            "queue_get_blocks": 0,
            "queue_get_errors": 0,
        }
        logger.debug("ParserWorker statistics reset")


class ParserWorkerPool:
    """Pool of parser workers for parallel processing.

    This class manages multiple ParserWorker instances to process files
    in parallel from a shared bounded queue.

    Attributes:
        max_workers: Maximum number of parser workers.
        parse_function: Function to parse individual files.
    """

    def __init__(
        self,
        parse_function: Callable[[str], Any],
        max_workers: Optional[int] = None,
    ) -> None:
        """Initialize the ParserWorkerPool.

        Args:
            parse_function: Function to parse individual files.
            max_workers: Maximum number of parser workers. If None, uses
                min(32, (os.cpu_count() or 1) + 4) as per ThreadPoolExecutor default.
        """
        self.parse_function = parse_function
        self.max_workers = max_workers

        # Initialize thread pool executor
        self._executor: Optional[ThreadPoolExecutor] = None

        # Parser workers
        self._workers: list[ParserWorker] = []

        logger.info(f"Initialized ParserWorkerPool with max_workers={max_workers}")

    def start(self) -> None:
        """Start the parser worker pool."""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
            self._workers = [
                ParserWorker(self.parse_function) for _ in range(self.max_workers or 1)
            ]
            logger.info(f"Started ParserWorkerPool with {len(self._workers)} workers")
        else:
            logger.warning("ParserWorkerPool already started")

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the parser worker pool.

        Args:
            wait: Whether to wait for all tasks to complete before shutdown.
        """
        if self._executor is not None:
            self._executor.shutdown(wait=wait)
            logger.info(f"Shutdown ParserWorkerPool (wait={wait})")
            self._executor = None
            self._workers = []

    def is_running(self) -> bool:
        """Check if the parser worker pool is running.

        Returns:
            True if the pool is active, False otherwise.
        """
        return self._executor is not None

    def submit_consume_task(
        self,
        file_queue: queue.Queue[Any],
        timeout: float = 1.0,
    ) -> list[Future[list[Any]]]:
        """Submit consume tasks to all parser workers.

        Args:
            file_queue: Bounded queue to get file paths from.
            timeout: Timeout for queue operations.

        Returns:
            List of Future objects representing the consume tasks.
        """
        if self._executor is None:
            raise RuntimeError("ParserWorkerPool not started. Call start() first.")

        futures = []
        for worker in self._workers:
            future = self._executor.submit(worker.consume_queue, file_queue, timeout)
            futures.append(future)
            logger.debug(f"Submitted consume task for worker: {worker}")

        return futures

    def get_stats(self) -> dict[str, Any]:
        """Get parser worker pool statistics.

        Returns:
            Dictionary containing parser worker pool statistics.
        """
        stats = {
            "is_running": self.is_running(),
            "max_workers": self.max_workers,
            "num_workers": len(self._workers),
            "has_parse_function": self.parse_function is not None,
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

        # Aggregate worker stats
        if self._workers:
            worker_stats = [worker.get_stats() for worker in self._workers]
            stats.update(
                {
                    "total_files_processed": sum(
                        ws["files_processed"] for ws in worker_stats
                    ),
                    "total_parse_successes": sum(
                        ws["parse_successes"] for ws in worker_stats
                    ),
                    "total_parse_errors": sum(
                        ws["parse_errors"] for ws in worker_stats
                    ),
                    "total_queue_get_blocks": sum(
                        ws["queue_get_blocks"] for ws in worker_stats
                    ),
                    "total_queue_get_errors": sum(
                        ws["queue_get_errors"] for ws in worker_stats
                    ),
                    "worker_stats": worker_stats,
                },
            )

        return stats
