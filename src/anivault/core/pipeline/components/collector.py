"""Result collector for AniVault pipeline.

This module provides the ResultCollector class that consumes processed
data from the output queue and stores it for final retrieval.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from pathlib import Path
from typing import Any

from anivault.core.pipeline.utils import BoundedQueue
from anivault.shared.constants import NetworkConfig, Pipeline
from anivault.shared.errors import (
    AniVaultError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
)
from anivault.shared.logging import log_operation_error, log_operation_success
from anivault.shared.metadata_models import FileMetadata


def _dict_to_file_metadata(result: dict[str, Any]) -> FileMetadata:
    """Convert parser result dictionary to FileMetadata.

    This function converts the dictionary structure returned by the parser
    worker into a type-safe FileMetadata dataclass instance.

    Args:
        result: Dictionary containing parsed file information with keys:
            - file_path: str (required)
            - file_name: str (used as title, required)
            - file_extension: str (converted to file_type, required)
            - file_size: int (optional, not stored in FileMetadata)
            - status: str (optional, not stored in FileMetadata)
            - worker_id: str (optional, not stored in FileMetadata)

    Returns:
        FileMetadata instance with converted data

    Raises:
        ValueError: If required fields are missing or invalid
        KeyError: If required keys are missing from result dict
    """
    file_path_str = result.get("file_path")
    if not file_path_str:
        msg = "file_path is required in result dictionary"
        raise ValueError(msg)

    file_path = Path(file_path_str)

    # Use file_name as title, fallback to file_path.name if not present
    title = result.get("file_name") or file_path.name
    if not title:
        msg = "file_name or valid file_path.name is required"
        raise ValueError(msg)

    # Extract file_type from file_extension, fallback to file_path.suffix
    file_extension = result.get("file_extension", "")
    if file_extension:
        # Remove leading dot if present
        file_type = file_extension.lstrip(".").lower()
    else:
        # Fallback to file_path suffix
        file_type = file_path.suffix.lstrip(".").lower() or "unknown"

    # Create FileMetadata instance
    # Note: year, season, episode are None as parser doesn't extract them
    # These will be populated later by enrichment process
    return FileMetadata(
        title=title,
        file_path=file_path,
        file_type=file_type,
        year=None,
        season=None,
        episode=None,
    )


class ResultCollector(threading.Thread):
    """Collector that processes results from the output queue.

    This class consumes processed file data from the output queue, storing it
    for final retrieval. Designed for both threaded and non-threaded usage.

    Args:
        output_queue: BoundedQueue instance to get processed results from.
        collector_id: Optional identifier for this collector.
    """

    def __init__(
        self,
        output_queue: BoundedQueue,
        collector_id: str | None = None,
    ) -> None:
        """Initialize the result collector.

        Args:
            output_queue: BoundedQueue instance to get processed results from.
            collector_id: Optional identifier for this collector.
        """
        super().__init__()
        self.output_queue = output_queue
        self.collector_id = collector_id or f"collector_{id(self) & 0xFFFF}"
        self._stopped = threading.Event()
        self._results: list[FileMetadata] = []
        self._lock = threading.Lock()

    def poll_once(self, timeout: float = 0.0) -> bool:
        """Process one item from the queue if available.

        Args:
            timeout: Maximum time to wait for an item (0.0 = non-blocking).

        Returns:
            True if an item was processed, False if queue was empty or
            sentinel received.
        """
        logger = logging.getLogger(__name__)
        context = ErrorContext(
            operation="poll_once",
            additional_data={"collector_id": self.collector_id, "timeout": timeout},
        )

        try:
            item = self._get_item_from_queue(timeout)

            # Check if we got an item from queue (None means timeout/empty)
            if item is None:
                return False

            # Handle sentinel first (even if it's None)
            if self._handle_sentinel(item):
                return False

            self._store_result_with_error_handling(item)
            return True

        except Exception as e:
            # Convert regular exception to InfrastructureError for logging
            if not hasattr(e, "context"):
                infrastructure_error = InfrastructureError(
                    ErrorCode.COLLECTOR_ERROR,
                    f"Poll once failed: {e}",
                    context,
                    original_error=e,
                )
                log_operation_error(
                    logger=logger,
                    error=infrastructure_error,
                    operation="poll_once",
                    context=context.safe_dict(),
                )
            elif isinstance(e, AniVaultError):
                log_operation_error(
                    logger=logger,
                    error=e,
                    operation="poll_once",
                    context=context.safe_dict(),
                )
            else:
                error = InfrastructureError(
                    code=ErrorCode.APPLICATION_ERROR,
                    message=f"Pipeline polling failed: {e!s}",
                    context=context,
                    original_error=e,
                )
                log_operation_error(
                    logger=logger,
                    error=error,
                    operation="poll_once",
                    context=context.safe_dict(),
                )
            raise InfrastructureError(
                ErrorCode.COLLECTOR_ERROR,
                f"Poll once failed: {e}",
                context,
                original_error=e,
            ) from e

    def run(
        self,
        max_idle_loops: int | None = None,
        idle_sleep: float = NetworkConfig.DEFAULT_TIMEOUT,
        get_timeout: float = NetworkConfig.DEFAULT_TIMEOUT,  # Increased timeout
    ) -> None:
        """Main collector loop that processes results from the output queue.

        Args:
            max_idle_loops: Maximum number of consecutive empty queue checks
                before stopping.
            idle_sleep: Sleep time between idle loops (0.0 = no sleep).
            get_timeout: Timeout for queue.get() calls.
        """
        logger = logging.getLogger(__name__)
        additional_data: dict[str, str | int | float | bool] = {
            "collector_id": self.collector_id,
            "idle_sleep": idle_sleep,
        }
        if max_idle_loops is not None:
            additional_data["max_idle_loops"] = max_idle_loops
        if get_timeout is not None:
            additional_data["get_timeout"] = get_timeout

        context = ErrorContext(
            operation="collector_run",
            additional_data=additional_data,
        )

        start_time = time.time()
        idle = 0

        try:
            while not self._stopped.is_set():
                try:
                    item = self._get_item_from_queue(get_timeout)
                    if item is None:
                        idle = self._handle_idle_state(idle, max_idle_loops, idle_sleep)
                        if idle >= max_idle_loops if max_idle_loops else False:
                            logger.warning(
                                (
                                    "ResultCollector %s: Max idle loops reached, "
                                    "stopping..."
                                ),
                                self.collector_id,
                            )
                            break
                        continue

                    # 성공적으로 아이템을 가져왔으므로 idle 카운트 리셋
                    idle = 0
                    logger.debug(
                        "ResultCollector %s: Received item: %s",
                        self.collector_id,
                        type(item).__name__,
                    )

                    if self._handle_sentinel(item):
                        break

                    self._store_result_with_error_handling(item)

                except (
                    ValueError,
                    RuntimeError,
                    KeyError,
                    TypeError,
                    AttributeError,
                ) as e:
                    # Handle specific errors from queue operations or data processing
                    self._handle_queue_error(e, context)
                    continue
                except InfrastructureError as e:
                    # Handle infrastructure errors from _store_result_with_error_handling
                    self._handle_queue_error(e, context)
                    continue

            duration_ms = (time.time() - start_time) * 1000
            log_operation_success(
                logger=logger,
                operation="collector_run",
                duration_ms=duration_ms,
                result_info={
                    "collector_id": self.collector_id,
                    "items_processed": len(self._results),
                },
                context=context.safe_dict(),
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            # Convert regular exception to InfrastructureError for logging
            if not hasattr(e, "context"):
                infrastructure_error = InfrastructureError(
                    ErrorCode.COLLECTOR_ERROR,
                    f"Collector run failed: {e}",
                    context,
                    original_error=e,
                )
                log_operation_error(
                    logger=logger,
                    error=infrastructure_error,
                    operation="collector_run",
                    context=context.safe_dict(),
                )
            elif isinstance(e, AniVaultError):
                log_operation_error(
                    logger=logger,
                    error=e,
                    operation="collector_run",
                    context=context.safe_dict(),
                )
            else:
                error = InfrastructureError(
                    code=ErrorCode.APPLICATION_ERROR,
                    message=f"Collector run failed: {e!s}",
                    context=context,
                    original_error=e,
                )
                log_operation_error(
                    logger=logger,
                    error=error,
                    operation="collector_run",
                    context=context.safe_dict(),
                )
            raise InfrastructureError(
                ErrorCode.COLLECTOR_ERROR,
                f"Collector run failed: {e}",
                context,
                original_error=e,
            ) from e
        finally:
            self.stop()  # 루프 종료 시 정지 플래그 세팅

    def _get_item_from_queue(self, timeout: float) -> Any | None:
        """Get an item from the output queue.

        Args:
            timeout: Maximum time to wait for an item.

        Returns:
            Item from queue or None if queue is empty (timeout).
        """
        try:
            return self.output_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _handle_idle_state(
        self,
        idle_count: int,
        _max_idle_loops: int | None,  # Used by caller, not in this method
        idle_sleep: float,
    ) -> int:
        """Handle idle state when no items are available.

        Args:
            idle_count: Current idle count.
            _max_idle_loops: Maximum number of idle loops (used by caller).
            idle_sleep: Sleep time between idle loops.

        Returns:
            Updated idle count.
        """
        idle_count += 1
        if idle_sleep:
            time.sleep(idle_sleep)
        return idle_count

    def _handle_sentinel(self, item: Any) -> bool:
        """Handle sentinel item.

        Args:
            item: Item to check for sentinel.

        Returns:
            True if sentinel was received and processing should stop.
        """
        if item is Pipeline.SENTINEL:
            logger = logging.getLogger(__name__)
            logger.info(
                "ResultCollector %s: Received sentinel, stopping...",
                self.collector_id,
            )
            try:
                self.output_queue.task_done()
            except (ValueError, RuntimeError) as e:
                # Handle specific queue operation errors
                logger.warning(
                    "Error marking task as done in collector %s: %s",
                    self.collector_id,
                    e,
                )
            self.stop()
            return True
        return False

    def _store_result_with_error_handling(self, result: dict[str, Any]) -> None:
        """Store result with error handling.

        Args:
            result: Result dictionary to convert and store.
        """
        logger = logging.getLogger(__name__)
        context = ErrorContext(
            operation="store_result",
            additional_data={
                "collector_id": self.collector_id,
                "result_status": result.get("status", "unknown"),
            },
        )

        try:
            # Convert dict to FileMetadata
            file_metadata = _dict_to_file_metadata(result)
            self._store_result(file_metadata)
            log_operation_success(
                logger=logger,
                operation="store_result",
                duration_ms=0.0,
                result_info={"result_status": result.get("status", "unknown")},
                context=context.safe_dict(),
            )
        except Exception as e:
            # Convert regular exception to InfrastructureError for logging
            if not hasattr(e, "context"):
                infrastructure_error = InfrastructureError(
                    ErrorCode.COLLECTOR_ERROR,
                    f"Failed to store result: {e}",
                    context,
                    original_error=e,
                )
                log_operation_error(
                    logger=logger,
                    error=infrastructure_error,
                    operation="store_result",
                    context=context.safe_dict(),
                )
            elif isinstance(e, AniVaultError):
                log_operation_error(
                    logger=logger,
                    error=e,
                    operation="store_result",
                    context=context.safe_dict(),
                )
            else:
                error = InfrastructureError(
                    code=ErrorCode.APPLICATION_ERROR,
                    message=f"Failed to store result: {e!s}",
                    context=context,
                    original_error=e,
                )
                log_operation_error(
                    logger=logger,
                    error=error,
                    operation="store_result",
                    context=context.safe_dict(),
                )
            raise InfrastructureError(
                ErrorCode.COLLECTOR_ERROR,
                f"Failed to store result: {e}",
                context,
                original_error=e,
            ) from e
        finally:
            try:
                self.output_queue.task_done()
            except (ValueError, RuntimeError) as e:
                # Handle specific queue operation errors
                logger.warning(
                    "Error marking task as done in collector %s: %s",
                    self.collector_id,
                    e,
                )

    def _handle_queue_error(self, error: Exception, context: ErrorContext) -> None:
        """Handle queue-related errors.

        Args:
            error: The error that occurred.
            context: Error context.
        """
        logger = logging.getLogger(__name__)

        # Log the error but don't re-raise for non-critical errors
        # Convert regular exception to InfrastructureError for logging
        if not hasattr(error, "context"):
            infrastructure_error = InfrastructureError(
                ErrorCode.QUEUE_OPERATION_ERROR,
                f"Queue operation failed: {error}",
                context,
                original_error=error,
            )
            log_operation_error(
                logger=logger,
                error=infrastructure_error,
                operation="queue_operation",
                context=context.safe_dict(),
            )
        elif isinstance(error, AniVaultError):
            log_operation_error(
                logger=logger,
                error=error,
                operation="queue_operation",
                context=context.safe_dict(),
            )
        else:
            infrastructure_error = InfrastructureError(
                code=ErrorCode.APPLICATION_ERROR,
                message=f"Queue operation failed: {error!s}",
                context=context,
                original_error=error,
            )
            log_operation_error(
                logger=logger,
                error=infrastructure_error,
                operation="queue_operation",
                context=context.safe_dict(),
            )

        # For critical errors, re-raise as InfrastructureError
        if isinstance(error, (OSError, RuntimeError)):
            raise InfrastructureError(
                ErrorCode.QUEUE_OPERATION_ERROR,
                f"Critical queue error: {error}",
                context,
                original_error=error,
            ) from error

    def _store_result(self, result: FileMetadata) -> None:
        """Store a processed result.

        Args:
            result: FileMetadata instance containing processed file information.
        """
        with self._lock:
            self._results.append(result)

    def get_results(self) -> list[FileMetadata]:
        """Get all collected results.

        Returns:
            List of FileMetadata instances containing processed file information.
        """
        with self._lock:
            return self._results.copy()

    def get_result_count(self) -> int:
        """Get the number of collected results.

        Returns:
            Number of results collected so far.
        """
        with self._lock:
            return len(self._results)

    def get_successful_results(self) -> list[FileMetadata]:
        """Get all collected results.

        Note: FileMetadata doesn't have a status field, so this method
        returns all results. Status filtering is handled at the dict level
        before conversion to FileMetadata.

        Returns:
            List of all FileMetadata instances (all are considered successful).
        """
        with self._lock:
            return self._results.copy()

    def get_failed_results(self) -> list[FileMetadata]:
        """Get failed results.

        Note: FileMetadata doesn't have a status field. Failed results
        are filtered at the dict level before conversion. This method
        returns an empty list as all stored results are successful.

        Returns:
            Empty list (failed results are not converted to FileMetadata).
        """
        with self._lock:
            return []

    def get_results_by_extension(self, extension: str) -> list[FileMetadata]:
        """Get results filtered by file extension.

        Args:
            extension: File extension to filter by (e.g., '.mp4', '.mkv').

        Returns:
            List of FileMetadata instances with the specified extension.
        """
        with self._lock:
            # Normalize extension (remove leading dot, lowercase)
            normalized_ext = extension.lstrip(".").lower()
            return [
                result
                for result in self._results
                if result.file_type.lower() == normalized_ext
            ]

    def get_results_by_worker(
        self,
        _worker_id: str,  # Unused, kept for API compatibility
    ) -> list[FileMetadata]:
        """Get results processed by a specific worker.

        Note: FileMetadata doesn't store worker_id. This method returns
        all results as worker information is not preserved after conversion.

        Args:
            worker_id: ID of the worker to filter by
                (unused, kept for API compatibility).

        Returns:
            List of all FileMetadata instances (worker filtering not available).
        """
        with self._lock:
            # Worker ID is not stored in FileMetadata, return all results
            return self._results.copy()

    def get_total_file_size(self) -> int:
        """Get the total size of all processed files.

        Note: FileMetadata doesn't store file_size. This method returns 0
        as file size information is not preserved after conversion.

        Returns:
            0 (file size is not stored in FileMetadata).
        """
        # FileMetadata doesn't have file_size field
        return 0

    def get_average_file_size(self) -> float:
        """Get the average size of processed files.

        Note: FileMetadata doesn't store file_size. This method returns 0.0
        as file size information is not preserved after conversion.

        Returns:
            0.0 (file size is not stored in FileMetadata).
        """
        # FileMetadata doesn't have file_size field
        return 0.0

    def get_file_extensions(self) -> list[str]:
        """Get a list of unique file extensions found.

        Returns:
            List of unique file extensions (from file_type field).
        """
        with self._lock:
            extensions = {
                result.file_type for result in self._results if result.file_type
            }
            return sorted(extensions)

    def get_worker_ids(self) -> list[str]:
        """Get a list of unique worker IDs that processed files.

        Note: FileMetadata doesn't store worker_id. This method returns
        an empty list as worker information is not preserved after conversion.

        Returns:
            Empty list (worker IDs are not stored in FileMetadata).
        """
        # FileMetadata doesn't have worker_id field
        return []

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of collected results.

        Returns:
            Dictionary containing summary statistics.
        """
        # 스냅샷 후 계산(재진입 회피)
        with self._lock:
            results = list(self._results)

        # 락 없이 계산
        total_results = len(results)

        # FileMetadata doesn't have status, file_size, or worker_id
        # All results are considered successful after conversion
        successful_results = results
        failed_results: list[FileMetadata] = []

        file_extensions = sorted({r.file_type for r in results if r.file_type})

        return {
            "total_results": total_results,
            "successful_results": len(successful_results),
            "failed_results": len(failed_results),
            "success_rate": 100.0 if total_results > 0 else 0.0,
            "total_file_size": 0,  # Not stored in FileMetadata
            "average_file_size": 0.0,  # Not stored in FileMetadata
            "file_extensions": file_extensions,
            "worker_ids": [],  # Not stored in FileMetadata
        }

    def clear_results(self) -> None:
        """Clear all collected results."""
        with self._lock:
            self._results.clear()

    def stop(self) -> None:
        """Signal the collector to stop processing."""
        self._stopped.set()

    def is_stopped(self) -> bool:
        """Check if the collector has been stopped.

        Returns:
            True if the collector has been stopped, False otherwise.
        """
        return self._stopped.is_set()

    def is_alive(self) -> bool:
        """Check if the collector is alive.

        For unit testing purposes, this always returns False since we don't
        use actual threads in unit tests.

        Returns:
            False (unit test mode).
        """
        return False


class ResultCollectorPool:
    """Pool of ResultCollector instances for parallel result collection.

    This class manages multiple ResultCollector instances to handle
    high-volume result collection from the output queue.
    """

    def __init__(
        self,
        output_queue: BoundedQueue,
        num_collectors: int = 1,
        collector_id_prefix: str | None = None,
    ) -> None:
        """Initialize the ResultCollector pool.

        Args:
            output_queue: Queue containing processed results to collect.
            num_collectors: Number of collector instances to create.
            collector_id_prefix: Optional prefix for collector IDs.
        """
        self.output_queue = output_queue
        self.num_collectors = num_collectors
        self.collector_id_prefix = collector_id_prefix or "collector"
        self.collectors: list[ResultCollector] = []
        self._started = False
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start all collector instances."""
        if self._started:
            raise RuntimeError("Collector pool has already been started")

        with self._lock:
            for i in range(self.num_collectors):
                collector_id = f"{self.collector_id_prefix}_{i}"
                collector = ResultCollector(
                    output_queue=self.output_queue,
                    collector_id=collector_id,
                )
                self.collectors.append(collector)
                collector.start()

            self._started = True

    def join(self, timeout: float | None = None) -> None:
        """Wait for all collector instances to complete.

        Args:
            timeout: Maximum time to wait for collectors to complete.
        """
        if not self._started:
            raise RuntimeError("Collector pool has not been started")

        for collector in self.collectors:
            collector.join(timeout=timeout)

    def stop(self) -> None:
        """Stop all collector instances gracefully."""
        for collector in self.collectors:
            collector.stop()
        self._started = False

    def is_alive(self) -> bool:
        """Check if any collector instances are still alive.

        Returns:
            True if any collector is alive, False otherwise.
        """
        return any(collector.is_alive() for collector in self.collectors)

    def get_collector_count(self) -> int:
        """Get the number of collector instances.

        Returns:
            Number of collector instances in the pool.
        """
        return len(self.collectors)

    def get_alive_collector_count(self) -> int:
        """Get the number of alive collector instances.

        Returns:
            Number of collectors that are currently alive.
        """
        return sum(1 for collector in self.collectors if collector.is_alive())

    def get_all_results(self) -> list[FileMetadata]:
        """Get all results from all collectors.

        Returns:
            Combined list of all FileMetadata instances from all collectors.
        """
        all_results: list[FileMetadata] = []
        for collector in self.collectors:
            all_results.extend(collector.get_results())
        return all_results

    def get_total_result_count(self) -> int:
        """Get total number of results from all collectors.

        Returns:
            Total number of results collected by all collectors.
        """
        return sum(collector.get_result_count() for collector in self.collectors)

    def get_pool_summary(self) -> dict[str, Any]:
        """Get summary information about the collector pool.

        Returns:
            Dictionary containing pool summary information.
        """
        all_results = self.get_all_results()
        # All results are considered successful after conversion to FileMetadata
        successful_results = all_results
        failed_results: list[FileMetadata] = []

        file_extensions = sorted({r.file_type for r in all_results if r.file_type})

        return {
            "num_collectors": self.num_collectors,
            "started": self._started,
            "alive_collectors": self.get_alive_collector_count(),
            "total_collectors": self.get_collector_count(),
            "total_results": len(all_results),
            "successful_results": len(successful_results),
            "failed_results": len(failed_results),
            "success_rate": 100.0 if all_results else 0.0,
            "total_file_size": 0,  # Not stored in FileMetadata
            "average_file_size": 0.0,  # Not stored in FileMetadata
            "file_extensions": file_extensions,
            "worker_ids": [],  # Not stored in FileMetadata
        }

    def clear_all_results(self) -> None:
        """Clear all results from all collectors."""
        for collector in self.collectors:
            collector.clear_results()
