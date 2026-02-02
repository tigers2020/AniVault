"""Parser worker and pool for AniVault pipeline.

This module provides the ParserWorker class (a threading.Thread subclass)
and ParserWorkerPool to consume file paths from the input queue and
process them concurrently.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any

from anivault.core.pipeline.components.cache import CacheV1
from anivault.core.pipeline.utils import BoundedQueue, ParserStatistics
from anivault.shared.constants import CoreCacheConfig, NetworkConfig
from anivault.shared.errors import (
    AniVaultError,
    AniVaultParsingError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
)
from anivault.shared.logging import log_operation_error, log_operation_success

logger = logging.getLogger(__name__)


class ParserWorker(threading.Thread):
    """Worker thread that processes files from the input queue.

    This class inherits from threading.Thread and processes file paths
    from the input queue, performing parsing operations and putting
    results into the output queue.

    Args:
        input_queue: BoundedQueue instance to get file paths from.
        output_queue: BoundedQueue instance to put processed results into.
        stats: ParserStatistics instance for tracking parser metrics.
        cache: CacheV1 instance for caching parsed results.
        worker_id: Optional identifier for this worker thread.
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        input_queue: BoundedQueue,
        output_queue: BoundedQueue,
        stats: ParserStatistics,
        cache: CacheV1,
        worker_id: str | None = None,
    ) -> None:
        """Initialize the parser worker.

        Args:
            input_queue: BoundedQueue instance to get file paths from.
            output_queue: BoundedQueue instance to put processed results into.
            stats: ParserStatistics instance for tracking parser metrics.
            cache: CacheV1 instance for caching parsed results.
            worker_id: Optional identifier for this worker thread.
        """
        super().__init__()
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.stats = stats
        self.cache = cache
        self.worker_id = worker_id or f"worker_{id(self)}"
        self._stop_event = threading.Event()

    def run(self) -> None:
        """Main worker loop that processes files from the input queue."""
        while not self._stop_event.is_set():
            try:
                # Get file path from input queue
                file_path = self.input_queue.get(timeout=NetworkConfig.DEFAULT_TIMEOUT)

                # Check for sentinel value (end of input)
                # Sentinel can be None or a special Sentinel object
                if file_path is None:
                    break

                # Skip if not a valid Path object (sentinel or other invalid value)
                if not isinstance(file_path, Path):
                    # Could be a sentinel object, stop processing
                    break

                # Process the file
                self._process_file(file_path)

            except (KeyError, ValueError, TypeError, AttributeError) as e:
                # Handle data processing errors
                logger.warning(
                    "Worker %d data processing error: %s",
                    self.worker_id,
                    str(e),
                )
                continue
            # pylint: disable-next=broad-exception-caught  # Handle timeout and other exceptions
            except Exception as e:
                # Handle timeout and other exceptions
                if "timeout" not in str(e).lower():
                    logger.exception(
                        "Worker %d unexpected error",
                        self.worker_id,
                    )
                continue

    def _process_file(self, file_path: Path) -> None:
        """Process a single file and update statistics.

        Args:
            file_path: Path to the file to process.
        """
        start_time = time.time()

        try:
            # Check cache first
            cached_result = self._check_cache(file_path)

            if cached_result:
                # Cache hit - use cached data
                self._handle_cache_hit(cached_result)
            else:
                # Cache miss - perform parsing
                self._handle_cache_miss(file_path)

            # Mark processing as successful
            duration_ms = (time.time() - start_time) * 1000
            log_operation_success(
                logger,
                "process_file",
                duration_ms,
                {"file_path": str(file_path), "worker_id": self.worker_id},
            )

        except (KeyError, ValueError, TypeError, AttributeError, IndexError) as e:
            # Handle data processing/parsing errors

            self.stats.increment_failures()
            duration_ms = (time.time() - start_time) * 1000

            # Create structured error
            context = ErrorContext(
                file_path=str(file_path),
                operation="process_file",
                additional_data={
                    "worker_id": self.worker_id,
                    "duration_ms": duration_ms,
                    "error_type": "data_processing",
                },
            )
            error = AniVaultParsingError(
                ErrorCode.PARSING_ERROR,
                f"Failed to process file due to data parsing error: {file_path}",
                context,
                original_error=e,
            )
            log_operation_error(logger, error)

        # pylint: disable-next=broad-exception-caught
        except Exception as e:  # noqa: BLE001
            # Handle unexpected errors

            self.stats.increment_failures()
            duration_ms = (time.time() - start_time) * 1000

            # Create structured error
            context = ErrorContext(
                file_path=str(file_path),
                operation="process_file",
                additional_data={
                    "worker_id": self.worker_id,
                    "duration_ms": duration_ms,
                    "error_type": "unexpected",
                },
            )
            unexpected_error = AniVaultError(
                ErrorCode.PARSER_ERROR,
                f"Failed to process file due to unexpected error: {file_path}",
                context,
                original_error=e,
            )
            log_operation_error(logger, unexpected_error)

        finally:
            # Always mark task as done
            self.input_queue.task_done()

    def _check_cache(self, file_path: Path) -> dict[str, Any] | None:
        """Check cache for file parsing result.

        Args:
            file_path: Path to the file to check in cache.

        Returns:
            Cached result if found, None otherwise.

        Raises:
            InfrastructureError: If cache operation fails.
        """
        try:
            # Generate cache key same way as _store_in_cache
            cache_key = self.cache._generate_key(  # pylint: disable=protected-access
                str(file_path),
                file_path.stat().st_mtime,
            )

            result = self.cache.get(cache_key)
            return result
        except (KeyError, ValueError, TypeError) as e:
            context = ErrorContext(
                file_path=str(file_path),
                operation="check_cache",
                additional_data={"worker_id": self.worker_id},
            )
            error = AniVaultParsingError(
                ErrorCode.CACHE_READ_FAILED,
                f"Failed to parse cached data for file: {file_path}",
                context,
                original_error=e,
            )
            log_operation_error(logger, error)
            raise error from e
        except Exception as e:  # pylint: disable=broad-exception-caught
            context = ErrorContext(
                file_path=str(file_path),
                operation="check_cache",
                additional_data={"worker_id": self.worker_id},
            )
            cache_error = AniVaultError(
                ErrorCode.CACHE_READ_FAILED,
                f"Failed to check cache for file: {file_path}",
                context,
                original_error=e,
            )
            log_operation_error(logger, cache_error)
            raise cache_error from e

    def _handle_cache_hit(self, cached_result: dict[str, Any]) -> None:
        """Handle cache hit scenario.

        Args:
            cached_result: Cached parsing result.

        Raises:
            InfrastructureError: If queue operation fails.
        """
        try:
            # Cache hit - use cached data
            self.stats.increment_cache_hit()
            self.stats.increment_items_processed()

            # Put result in output queue
            self.output_queue.put(cached_result)

            # Update success/failure statistics
            if cached_result.get("status") == "success":
                self.stats.increment_successes()
            else:
                self.stats.increment_failures()

            log_operation_success(
                logger,
                "handle_cache_hit",
                0.0,  # Cache hit is instant
                {"worker_id": self.worker_id},
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            context = ErrorContext(
                operation="handle_cache_hit",
                additional_data={"worker_id": self.worker_id},
            )
            error = InfrastructureError(
                ErrorCode.QUEUE_OPERATION_ERROR,
                "Failed to handle cache hit result",
                context,
                original_error=e,
            )
            log_operation_error(logger, error)
            raise error from e

    def _handle_cache_miss(self, file_path: Path) -> None:
        """Handle cache miss scenario by performing parsing.

        Args:
            file_path: Path to the file to parse.

        Raises:
            InfrastructureError: If parsing or cache operations fail.
        """
        try:
            # Cache miss - perform parsing
            self.stats.increment_cache_miss()
            self.stats.increment_items_processed()

            # Perform placeholder parsing
            result = self._parse_file(file_path)

            # Store result in cache (24 hours TTL)
            self._store_in_cache(file_path, result)

            # Put result in output queue
            self.output_queue.put(result)

            # Check if parsing was successful
            if result.get("status") == "success":
                self.stats.increment_successes()
            else:
                self.stats.increment_failures()

            log_operation_success(
                logger,
                "handle_cache_miss",
                0.0,  # Duration will be logged by parent
                {"file_path": str(file_path), "worker_id": self.worker_id},
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            context = ErrorContext(
                file_path=str(file_path),
                operation="handle_cache_miss",
                additional_data={"worker_id": self.worker_id},
            )
            error = InfrastructureError(
                ErrorCode.PARSER_ERROR,
                f"Failed to handle cache miss for file: {file_path}",
                context,
                original_error=e,
            )
            log_operation_error(logger, error)
            raise error from e

    def _store_in_cache(self, file_path: Path, result: dict[str, Any]) -> None:
        """Store parsing result in cache.

        Args:
            file_path: Path to the file that was parsed.
            result: Parsing result to store.

        Raises:
            InfrastructureError: If cache operation fails.
        """
        try:
            # Store result in cache (24 hours TTL)
            mtime = file_path.stat().st_mtime
            cache_key = self.cache._generate_key(  # pylint: disable=protected-access
                str(file_path),
                mtime,
            )

            self.cache.set_cache(
                cache_key,
                result,
                ttl_seconds=CoreCacheConfig.DEFAULT_TTL,
            )

            log_operation_success(
                logger,
                "store_in_cache",
                0.0,  # Cache operation is instant
                {"file_path": str(file_path), "worker_id": self.worker_id},
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            context = ErrorContext(
                file_path=str(file_path),
                operation="store_in_cache",
                additional_data={"worker_id": self.worker_id},
            )
            error = InfrastructureError(
                ErrorCode.CACHE_WRITE_FAILED,
                f"Failed to store result in cache for file: {file_path}",
                context,
                original_error=e,
            )
            log_operation_error(logger, error)
            raise error from e

    def _parse_file(self, file_path: Path) -> dict[str, Any]:
        """Parse a file and extract metadata using anitopy.

        Uses AnitopyParser to extract anime title, episode, season, year from
        filename. Falls back to raw filename when parsing fails.

        Args:
            file_path: Path to the file to parse.

        Returns:
            Dictionary containing parsed file information with keys:
            file_path, file_name (anime_title or filename), file_extension,
            episode_number, anime_season, anime_year (when extracted).
        """
        try:
            stat_info = file_path.stat()
            file_ext = file_path.suffix.lower()
            file_name = file_path.name
            episode_number: int | None = None
            anime_season: int | None = None
            anime_year: int | None = None

            try:
                from anivault.core.parser.anitopy_parser import AnitopyParser

                parsed = AnitopyParser().parse(file_name)
                anime_title = parsed.title if parsed.title else None
                episode_number = parsed.episode
                anime_season = parsed.season
                anime_year = parsed.year
                display_name = anime_title if anime_title else file_name
            except (ImportError, Exception):  # noqa: BLE001 - intentional fallback on any parse failure
                display_name = file_name

            result: dict[str, Any] = {
                "file_path": str(file_path),
                "file_name": display_name,
                "file_size": stat_info.st_size,
                "file_extension": file_ext,
                "modified_time": stat_info.st_mtime,
                "created_time": stat_info.st_ctime,
                "worker_id": self.worker_id,
                "status": "success",
            }
            if episode_number is not None:
                result["episode_number"] = episode_number
            if anime_season is not None:
                result["anime_season"] = anime_season
            if anime_year is not None:
                result["anime_year"] = anime_year

            log_operation_success(
                logger,
                "parse_file",
                0.0,
                {"file_path": str(file_path), "worker_id": self.worker_id},
            )
            return result

        except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            # Create structured error context
            context = ErrorContext(
                file_path=str(file_path),
                operation="parse_file",
                additional_data={"worker_id": self.worker_id},
            )
            error = InfrastructureError(
                ErrorCode.PARSING_ERROR,
                f"Failed to parse file: {file_path}",
                context,
                original_error=e,
            )
            log_operation_error(logger, error)

            # Return error result (don't raise to allow graceful handling)
            return {
                "file_path": str(file_path),
                "file_name": file_path.name if file_path else "unknown",
                "error": str(e),
                "worker_id": self.worker_id,
                "status": "error",
            }

    def stop(self) -> None:
        """Signal the worker to stop processing."""
        self._stop_event.set()


class ParserWorkerPool:
    """Pool of ParserWorker threads for concurrent file processing.

    This class manages a collection of ParserWorker threads and provides
    methods to start and stop the worker pool.

    Args:
        num_workers: Number of worker threads to create.
        input_queue: BoundedQueue instance to get file paths from.
        output_queue: BoundedQueue instance to put processed results into.
        stats: ParserStatistics instance for tracking parser metrics.
        cache: CacheV1 instance for caching parsed results.
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        num_workers: int,
        input_queue: BoundedQueue,
        output_queue: BoundedQueue,
        stats: ParserStatistics,
        cache: CacheV1,
        enable_dynamic_adjustment: bool = False,
    ) -> None:
        """Initialize the parser worker pool.

        Args:
            num_workers: Number of worker threads to create.
            input_queue: BoundedQueue instance to get file paths from.
            output_queue: BoundedQueue instance to put processed results into.
            stats: ParserStatistics instance for tracking parser metrics.
            cache: CacheV1 instance for caching parsed results.
            enable_dynamic_adjustment: Whether to enable dynamic worker adjustment
                                     based on queue sizes. Default is False.
        """
        self.num_workers = num_workers
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.stats = stats
        self.cache = cache
        self.workers: list[ParserWorker] = []
        self._started = False
        self.enable_dynamic_adjustment = enable_dynamic_adjustment
        # Optimal ratio: 1 worker per 100-200 queue items (configurable)
        self.optimal_queue_worker_ratio = 150

    def start(self) -> None:
        """Start all worker threads."""
        if self._started:
            raise RuntimeError("Worker pool has already been started")

        # Create and start worker threads
        for i in range(self.num_workers):
            worker = ParserWorker(
                input_queue=self.input_queue,
                output_queue=self.output_queue,
                stats=self.stats,
                cache=self.cache,
                worker_id=f"worker_{i}",
            )
            self.workers.append(worker)
            worker.start()

        self._started = True

    def join(self, timeout: float | None = None) -> None:
        """Wait for all worker threads to complete.

        Args:
            timeout: Maximum time to wait for threads to complete.
        """
        if not self._started:
            raise RuntimeError("Worker pool has not been started")

        for worker in self.workers:
            worker.join(timeout=timeout)

    def stop(self) -> None:
        """Stop all worker threads gracefully."""
        for worker in self.workers:
            worker.stop()
        self._started = False

    def is_alive(self) -> bool:
        """Check if any worker threads are still alive.

        Returns:
            True if any worker thread is alive, False otherwise.
        """
        return any(worker.is_alive() for worker in self.workers)

    def get_worker_count(self) -> int:
        """Get the number of worker threads.

        Returns:
            Number of worker threads in the pool.
        """
        return len(self.workers)

    def get_alive_worker_count(self) -> int:
        """Get the number of alive worker threads.

        Returns:
            Number of worker threads that are currently alive.
        """
        return sum(1 for worker in self.workers if worker.is_alive())

    def get_pool_status(self) -> dict[str, Any]:
        """Get status information about the worker pool.

        Returns:
            Dictionary containing pool status information.
        """
        input_size = self.input_queue.size()
        output_size = self.output_queue.size()
        return {
            "num_workers": self.num_workers,
            "started": self._started,
            "alive_workers": self.get_alive_worker_count(),
            "total_workers": self.get_worker_count(),
            "input_queue_size": input_size,
            "output_queue_size": output_size,
            "items_processed": self.stats.items_processed,
            "successes": self.stats.successes,
            "failures": self.stats.failures,
            "optimal_worker_count": self._calculate_optimal_worker_count(),
        }

    def _calculate_optimal_worker_count(self) -> int:
        """Calculate optimal worker count based on queue sizes.

        Uses the formula: optimal_workers = max(1, queue_size / optimal_ratio)
        Considers both input and output queue sizes.

        Returns:
            Recommended number of workers based on current queue state.
        """
        if not self.enable_dynamic_adjustment:
            return self.num_workers

        input_size = self.input_queue.size()
        output_size = self.output_queue.size()
        # Use the larger queue size to determine optimal workers
        max_queue_size = max(input_size, output_size)

        # Calculate optimal workers: 1 worker per optimal_ratio items
        optimal = max(1, max_queue_size // self.optimal_queue_worker_ratio)
        # Cap at reasonable maximum (e.g., 2x current workers or 32, whichever is smaller)
        max_workers = min(32, self.num_workers * 2)
        return min(optimal, max_workers)
