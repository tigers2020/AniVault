"""File Processing Queue System.

This module provides a robust producer-consumer pattern for file processing,
supporting both ThreadPoolExecutor and ProcessPoolExecutor with configurable
worker limits and graceful shutdown mechanisms.
"""

import logging
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union, Iterator
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QueueStatus(Enum):
    """Status of the file processing queue."""
    IDLE = "idle"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class QueueConfig:
    """Configuration for the file processing queue."""
    max_queue_size: int = 1000
    batch_size: int = 10
    timeout_seconds: float = 30.0
    progress_callback: Optional[Callable[[int, int, str], None]] = None
    error_callback: Optional[Callable[[Exception, Any], None]] = None


@dataclass
class QueueStats:
    """Statistics for the file processing queue."""
    total_items: int = 0
    processed_items: int = 0
    failed_items: int = 0
    queued_items: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100

    @property
    def processing_time(self) -> float:
        """Calculate total processing time in seconds."""
        if self.start_time is None:
            return 0.0
        end_time = self.end_time or time.time()
        return end_time - self.start_time

    @property
    def items_per_second(self) -> float:
        """Calculate processing rate in items per second."""
        if self.processing_time == 0:
            return 0.0
        return self.processed_items / self.processing_time


class FileProcessingQueue:
    """Robust file processing queue with producer-consumer pattern.

    Supports both ThreadPoolExecutor and ProcessPoolExecutor with configurable
    worker limits and graceful shutdown mechanisms.
    """

    def __init__(
        self,
        config: Optional[QueueConfig] = None,
        executor_type: str = "thread",
        max_workers: Optional[int] = None,
        operation_type: str = "general_io"
    ) -> None:
        """Initialize the file processing queue.

        Args:
            config: Queue configuration
            executor_type: Type of executor ('thread' or 'process')
            max_workers: Maximum number of workers (overrides default)
            operation_type: Type of operation for executor selection
        """
        self.config = config or QueueConfig()
        self.executor_type = executor_type
        self.max_workers = max_workers
        self.operation_type = operation_type
        
        # Queue and synchronization
        self._queue: queue.Queue = queue.Queue(maxsize=self.config.max_queue_size)
        self._lock = threading.Lock()
        self._status = QueueStatus.IDLE
        self._stats = QueueStats()
        
        # Executor management
        self._executor: Optional[Union[ThreadPoolExecutor, ProcessPoolExecutor]] = None
        self._futures: List[Any] = []
        
        # Worker management
        self._workers_started = False
        self._shutdown_event = threading.Event()
        
        logger.info(
            f"FileProcessingQueue initialized: type={executor_type}, "
            f"operation={operation_type}, max_queue_size={self.config.max_queue_size}"
        )

    def _create_executor(self) -> Union[ThreadPoolExecutor, ProcessPoolExecutor]:
        """Create the appropriate executor based on configuration.

        Returns:
            Union[ThreadPoolExecutor, ProcessPoolExecutor]: Configured executor
        """
        import os
        
        # Determine worker count
        if self.max_workers is not None:
            workers = self.max_workers
        elif self.executor_type == "thread":
            # For I/O-bound tasks, use more workers than CPU cores
            cpu_count = os.cpu_count() or 4
            workers = min(32, max(4, int(cpu_count * 1.5)))
        else:  # process
            # For CPU-bound tasks, use all available cores
            workers = os.cpu_count() or 4

        # Create executor
        if self.executor_type == "thread":
            executor = ThreadPoolExecutor(
                max_workers=workers,
                thread_name_prefix=f"{self.operation_type.title()}Worker"
            )
            logger.info(f"Created ThreadPoolExecutor with {workers} workers")
        else:  # process
            executor = ProcessPoolExecutor(max_workers=workers)
            logger.info(f"Created ProcessPoolExecutor with {workers} workers")

        return executor

    def add_items(self, items: List[Any]) -> int:
        """Add items to the processing queue.

        Args:
            items: List of items to process

        Returns:
            int: Number of items successfully added to queue

        Raises:
            RuntimeError: If queue is not in IDLE or RUNNING status
        """
        with self._lock:
            if self._status not in [QueueStatus.IDLE, QueueStatus.RUNNING]:
                raise RuntimeError(f"Cannot add items when queue status is {self._status}")

            added_count = 0
            for item in items:
                try:
                    self._queue.put_nowait(item)
                    added_count += 1
                except queue.Full:
                    logger.warning(f"Queue is full, could not add item: {item}")
                    break

            self._stats.total_items += added_count
            self._stats.queued_items += added_count

            logger.debug(f"Added {added_count} items to queue")
            return added_count

    def add_item(self, item: Any) -> bool:
        """Add a single item to the processing queue.

        Args:
            item: Item to process

        Returns:
            bool: True if item was added successfully

        Raises:
            RuntimeError: If queue is not in IDLE or RUNNING status
        """
        return self.add_items([item]) > 0

    def start_processing(
        self,
        worker_function: Callable[[Any], Any],
        batch_processing: bool = False
    ) -> None:
        """Start processing items in the queue.

        Args:
            worker_function: Function to process each item
            batch_processing: If True, process items in batches

        Raises:
            RuntimeError: If queue is not in IDLE status
            ValueError: If worker_function is not callable
        """
        if not callable(worker_function):
            raise ValueError("worker_function must be callable")

        with self._lock:
            if self._status != QueueStatus.IDLE:
                raise RuntimeError(f"Cannot start processing when queue status is {self._status}")

            self._status = QueueStatus.RUNNING
            self._stats.start_time = time.time()
            self._stats.end_time = None
            self._shutdown_event.clear()

        # Create executor
        self._executor = self._create_executor()

        try:
            if batch_processing:
                self._process_batches(worker_function)
            else:
                self._process_items(worker_function)
        except Exception as e:
            logger.error(f"Error during processing: {e}")
            with self._lock:
                self._status = QueueStatus.ERROR
            raise
        finally:
            self._cleanup()
            with self._lock:
                if self._status != QueueStatus.ERROR:
                    self._status = QueueStatus.STOPPED

    def _process_items(self, worker_function: Callable[[Any], Any]) -> None:
        """Process items individually.

        Args:
            worker_function: Function to process each item
        """
        logger.info("Starting individual item processing")

        while not self._shutdown_event.is_set():
            try:
                # Get item from queue with timeout
                item = self._queue.get(timeout=1.0)
                
                # Submit to executor
                future = self._executor.submit(worker_function, item)
                self._futures.append(future)
                
                # Process completed futures
                self._process_completed_futures()

            except queue.Empty:
                # No items available, check if we should continue
                with self._lock:
                    if self._stats.queued_items == 0 and not self._futures:
                        logger.info("No more items to process")
                        break
                # Continue the loop to check shutdown event
                continue
            except Exception as e:
                logger.error(f"Error processing item: {e}")
                if self.config.error_callback:
                    self.config.error_callback(e, None)

        # Wait for remaining futures to complete
        self._wait_for_futures()

    def _process_batches(self, worker_function: Callable[[Any], Any]) -> None:
        """Process items in batches.

        Args:
            worker_function: Function to process each batch
        """
        logger.info(f"Starting batch processing with batch size {self.config.batch_size}")

        # Process all items in batches
        empty_iterations = 0
        max_empty_iterations = 100  # Prevent infinite loop
        
        while not self._shutdown_event.is_set() and empty_iterations < max_empty_iterations:
            # Collect batch from queue
            batch = []
            
            # Try to get items for the batch
            for _ in range(self.config.batch_size):
                if self._shutdown_event.is_set():
                    break
                    
                try:
                    item = self._queue.get_nowait()
                    batch.append(item)
                except queue.Empty:
                    break

            # If no items collected, check if we should exit
            if not batch:
                empty_iterations += 1
                
                # Check if queue is empty and no futures are running
                with self._lock:
                    queue_empty = self._queue.empty()
                    no_futures = not self._futures
                    
                if queue_empty and no_futures:
                    logger.info("No more items to process in batch mode")
                    break
                elif empty_iterations < max_empty_iterations:
                    # Small delay before checking again, but limit iterations
                    time.sleep(0.01)
                    continue
                else:
                    logger.warning("Max empty iterations reached, forcing exit from batch processing")
                    break
            else:
                empty_iterations = 0  # Reset counter when we process items

            # Submit batch to executor
            future = self._executor.submit(worker_function, batch)
            self._futures.append(future)

            # Process completed futures
            self._process_completed_futures()
            
            # Update queued_items count for batch processing
            with self._lock:
                # In batch processing, queued_items should reflect items still in queue + futures
                self._stats.queued_items = self._queue.qsize() + len(self._futures)

        # Wait for remaining futures to complete
        self._wait_for_futures()

    def _process_completed_futures(self) -> None:
        """Process completed futures and update statistics."""
        completed_futures = []

        # Find completed futures (thread-safe)
        with self._lock:
            for future in self._futures:
                if future.done():
                    completed_futures.append(future)

        # Process completed futures
        for future in completed_futures:
            # Remove from futures list (thread-safe)
            with self._lock:
                if future in self._futures:
                    self._futures.remove(future)
                else:
                    # Future was already processed, skip
                    continue
            
            try:
                result = future.result()
                # Determine how many items were processed based on result type
                if isinstance(result, list):
                    # Batch processing - result is a list of processed items
                    batch_size = len(result)
                else:
                    # Individual processing - single item
                    batch_size = 1
                
                with self._lock:
                    self._stats.processed_items += batch_size
                    self._stats.queued_items -= batch_size
                
                # Call progress callback
                if self.config.progress_callback:
                    self.config.progress_callback(
                        self._stats.processed_items,
                        self._stats.total_items,
                        "Processing completed"
                    )

            except Exception as e:
                logger.error(f"Error processing future: {e}")
                # For failed futures, we don't know the exact batch size
                # so we'll update stats conservatively
                with self._lock:
                    self._stats.failed_items += 1
                    # Don't decrease queued_items for failed futures as they're still "queued"
                
                if self.config.error_callback:
                    self.config.error_callback(e, None)

    def _wait_for_futures(self) -> None:
        """Wait for all remaining futures to complete."""
        logger.info(f"Waiting for {len(self._futures)} remaining futures to complete")

        if not self._futures:
            return

        # Process remaining futures that haven't been processed yet
        remaining_futures = [f for f in self._futures if not f.done()]
        
        if not remaining_futures:
            logger.info("No remaining futures to wait for")
            self._futures.clear()
            return
        
        try:
            for future in as_completed(remaining_futures, timeout=60.0):
                try:
                    result = future.result()
                    # Determine how many items were processed based on result type
                    if isinstance(result, list):
                        # Batch processing - result is a list of processed items
                        batch_size = len(result)
                    else:
                        # Individual processing - single item
                        batch_size = 1
                    
                    with self._lock:
                        self._stats.processed_items += batch_size
                        self._stats.queued_items -= batch_size
                except Exception as e:
                    logger.error(f"Error processing future: {e}")
                    with self._lock:
                        self._stats.failed_items += 1
                        # Don't decrease queued_items for failed futures
        except TimeoutError:
            logger.warning(f"Timeout waiting for {len(remaining_futures)} futures to complete")
            # Cancel any remaining futures that haven't completed
            for future in remaining_futures:
                if not future.done():
                    future.cancel()
                    with self._lock:
                        self._stats.failed_items += 1
                        # Don't decrease queued_items for cancelled futures
        except Exception as e:
            logger.error(f"Unexpected error in _wait_for_futures: {e}")
            # Ensure we don't leave futures hanging
            for future in remaining_futures:
                if not future.done():
                    future.cancel()

        self._futures.clear()

    def stop_processing(self, wait: bool = True) -> None:
        """Stop processing items in the queue.

        Args:
            wait: If True, wait for current tasks to complete
        """
        logger.info("Stopping file processing queue")

        with self._lock:
            if self._status == QueueStatus.RUNNING:
                self._status = QueueStatus.STOPPING

        # Signal shutdown
        self._shutdown_event.set()

        if wait:
            self._wait_for_futures()

        with self._lock:
            self._status = QueueStatus.STOPPED

        self._cleanup()

    def _cleanup(self) -> None:
        """Clean up resources."""
        if self._executor:
            logger.info("Shutting down executor")
            self._executor.shutdown(wait=True)
            self._executor = None

        with self._lock:
            self._stats.end_time = time.time()

    def get_status(self) -> QueueStatus:
        """Get current queue status.

        Returns:
            QueueStatus: Current status of the queue
        """
        with self._lock:
            return self._status

    def get_stats(self) -> QueueStats:
        """Get current queue statistics.

        Returns:
            QueueStats: Current statistics of the queue
        """
        with self._lock:
            return QueueStats(
                total_items=self._stats.total_items,
                processed_items=self._stats.processed_items,
                failed_items=self._stats.failed_items,
                queued_items=self._stats.queued_items,
                start_time=self._stats.start_time,
                end_time=self._stats.end_time
            )

    def is_empty(self) -> bool:
        """Check if the queue is empty.

        Returns:
            bool: True if queue is empty
        """
        return self._queue.empty()

    def queue_size(self) -> int:
        """Get current queue size.

        Returns:
            int: Number of items currently in queue
        """
        return self._queue.qsize()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_processing(wait=True)
