"""Main pipeline orchestrator for AniVault.

This module provides the main entry point for running the complete
file processing pipeline: Scanner → ParserWorkerPool → ResultCollector.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from anivault.core.pipeline.cache import CacheV1
from anivault.core.pipeline.collector import ResultCollector
from anivault.core.pipeline.parser import ParserWorkerPool
from anivault.core.pipeline.scanner import DirectoryScanner
from anivault.core.pipeline.utils import (
    BoundedQueue,
    ParserStatistics,
    QueueStatistics,
    ScanStatistics,
)
from anivault.shared.constants import Pipeline, Timeout
from anivault.shared.errors import ErrorCode, ErrorContext, InfrastructureError
from anivault.shared.logging import log_operation_error, log_operation_success

logger = logging.getLogger(__name__)


def format_statistics(
    scan_stats: ScanStatistics,
    queue_stats: QueueStatistics,
    parser_stats: ParserStatistics,
    total_duration: float,
) -> str:
    """Format pipeline statistics into a human-readable report.

    Args:
        scan_stats: ScanStatistics instance with scanning metrics.
        queue_stats: QueueStatistics instance with queue metrics.
        parser_stats: ParserStatistics instance with parser metrics.
        total_duration: Total pipeline execution time in seconds.

    Returns:
        A formatted multi-line string containing all statistics.
    """
    # Calculate success/failure percentages
    total_processed = parser_stats.items_processed
    success_rate = (
        (parser_stats.successes / total_processed * 100) if total_processed > 0 else 0
    )
    failure_rate = (
        (parser_stats.failures / total_processed * 100) if total_processed > 0 else 0
    )

    # Calculate cache hit/miss percentages
    total_cache_ops = parser_stats.cache_hits + parser_stats.cache_misses
    cache_hit_rate = (
        (parser_stats.cache_hits / total_cache_ops * 100) if total_cache_ops > 0 else 0
    )
    cache_miss_rate = (
        (parser_stats.cache_misses / total_cache_ops * 100)
        if total_cache_ops > 0
        else 0
    )

    # Build the statistics report
    lines = [
        "",
        "=" * 60,
        "                    PIPELINE STATISTICS",
        "=" * 60,
        "",
        "Timing:",
        f"  - Total pipeline time:  {total_duration:.2f}s",
        "",
        "Scanner:",
        f"  - Files scanned:        {scan_stats.files_scanned:,}",
        f"  - Directories scanned:  {scan_stats.directories_scanned:,}",
        "",
        "Queue:",
        f"  - Items put:            {queue_stats.items_put:,}",
        f"  - Items got:            {queue_stats.items_got:,}",
        f"  - Peak size:            {queue_stats.max_size:,}",
        "",
        "Parser:",
        f"  - Items processed:      {parser_stats.items_processed:,}",
        f"  - Successful:           {parser_stats.successes:,} ({success_rate:.2f}%)",
        f"  - Failed:               {parser_stats.failures:,} ({failure_rate:.2f}%)",
        "",
        "Cache:",
        f"  - Cache hits:           {parser_stats.cache_hits:,} ({cache_hit_rate:.2f}%)",
        f"  - Cache misses:         {parser_stats.cache_misses:,} ({cache_miss_rate:.2f}%)",
        "",
        "=" * 60,
        "",
    ]

    return "\n".join(lines)


def _create_pipeline_components(
    root_path: str,
    extensions: list[str],
    num_workers: int,
    max_queue_size: int,
    cache_path: str | None = None,
) -> tuple[
    ScanStatistics,
    QueueStatistics,
    ParserStatistics,
    CacheV1,
    BoundedQueue,
    BoundedQueue,
    DirectoryScanner,
    ParserWorkerPool,
    ResultCollector,
]:
    """Create and initialize all pipeline components.

    Args:
        root_path: Root directory to scan for files.
        extensions: List of file extensions to scan for.
        num_workers: Number of parser worker threads.
        max_queue_size: Maximum size for bounded queues.
        cache_path: Optional path to cache file for storing scan results.

    Returns:
        Tuple containing all pipeline components.

    Raises:
        InfrastructureError: If component initialization fails.
    """
    context = ErrorContext(
        operation="create_pipeline_components",
        additional_data={
            "root_path": root_path,
            "extensions": extensions,
            "num_workers": num_workers,
            "max_queue_size": max_queue_size,
        },
    )

    try:
        # Create statistics objects for each component
        scan_stats = ScanStatistics()
        queue_stats = QueueStatistics()
        parser_stats = ParserStatistics()

        # Create cache instance
        cache = CacheV1(cache_dir=Path("cache"))

        # Create bounded queues for inter-component communication
        file_queue = BoundedQueue(maxsize=max_queue_size)
        result_queue = BoundedQueue(maxsize=max_queue_size)

        # Initialize pipeline components
        scanner = DirectoryScanner(
            root_path=Path(root_path),
            input_queue=file_queue,
            extensions=extensions,
            stats=scan_stats,
        )

        parser_pool = ParserWorkerPool(
            num_workers=num_workers,
            input_queue=file_queue,
            output_queue=result_queue,
            stats=parser_stats,
            cache=cache,
        )

        collector = ResultCollector(
            output_queue=result_queue,
            collector_id="main_collector",
        )

        log_operation_success(
            logger=logger,
            operation="create_pipeline_components",
            duration_ms=0.0,
            context=context.to_dict(),
        )

        return (
            scan_stats,
            queue_stats,
            parser_stats,
            cache,
            file_queue,
            result_queue,
            scanner,
            parser_pool,
            collector,
        )

    except Exception as e:
        infrastructure_error = InfrastructureError(
            ErrorCode.PIPELINE_INITIALIZATION_ERROR,
            f"Failed to create pipeline components: {e}",
            context,
            original_error=e,
        )
        log_operation_error(
            logger=logger,
            error=infrastructure_error,
            operation="create_pipeline_components",
            context=context.to_dict(),
        )
        raise InfrastructureError(
            ErrorCode.PIPELINE_INITIALIZATION_ERROR,
            f"Failed to create pipeline components: {e}",
            context,
            original_error=e,
        ) from e


def _start_pipeline_components(
    scanner: DirectoryScanner,
    parser_pool: ParserWorkerPool,
    collector: ResultCollector,
    num_workers: int,
) -> None:
    """Start all pipeline components.

    Args:
        scanner: DirectoryScanner instance.
        parser_pool: ParserWorkerPool instance.
        collector: ResultCollector instance.
        num_workers: Number of worker threads.

    Raises:
        InfrastructureError: If component startup fails.
    """
    context = ErrorContext(
        operation="start_pipeline_components",
        additional_data={"num_workers": num_workers},
    )

    try:
        # Start all pipeline components
        logger.info("Starting scanner...")
        scanner.start()

        logger.info("Starting parser pool with %s workers...", num_workers)
        parser_pool.start()

        logger.info("Starting result collector...")
        collector.start()

        log_operation_success(
            logger=logger,
            operation="start_pipeline_components",
            duration_ms=0.0,
            context=context.to_dict(),
        )

    except Exception as e:
        infrastructure_error = InfrastructureError(
            ErrorCode.PIPELINE_EXECUTION_ERROR,
            f"Failed to start pipeline components: {e}",
            context,
            original_error=e,
        )
        log_operation_error(
            logger=logger,
            error=infrastructure_error,
            operation="start_pipeline_components",
            context=context.to_dict(),
        )
        raise InfrastructureError(
            ErrorCode.PIPELINE_EXECUTION_ERROR,
            f"Failed to start pipeline components: {e}",
            context,
            original_error=e,
        ) from e


def _wait_for_scanner_completion(
    scanner: DirectoryScanner,
    scan_stats: ScanStatistics,
) -> None:
    """Wait for scanner to complete and log results.

    Args:
        scanner: DirectoryScanner instance.
        scan_stats: ScanStatistics instance.

    Raises:
        InfrastructureError: If scanner completion fails.
    """
    context = ErrorContext(
        operation="wait_for_scanner_completion",
        additional_data={"files_scanned": scan_stats.files_scanned},
    )

    try:
        logger.info("Waiting for scanner to complete...")
        scanner.join()
        logger.info("Scanner completed. Found %s files.", scan_stats.files_scanned)

        log_operation_success(
            logger=logger,
            operation="wait_for_scanner_completion",
            duration_ms=0.0,
            context=context.to_dict(),
        )

    except Exception as e:
        infrastructure_error = InfrastructureError(
            ErrorCode.SCANNER_ERROR,
            f"Scanner completion failed: {e}",
            context,
            original_error=e,
        )
        log_operation_error(
            logger=logger,
            error=infrastructure_error,
            operation="wait_for_scanner_completion",
            context=context.to_dict(),
        )
        raise InfrastructureError(
            ErrorCode.SCANNER_ERROR,
            f"Scanner completion failed: {e}",
            context,
            original_error=e,
        ) from e


def _signal_parser_shutdown(
    file_queue: BoundedQueue,
    num_workers: int,
) -> None:
    """Signal parser workers to shut down by sending sentinel values.

    Args:
        file_queue: BoundedQueue for file paths.
        num_workers: Number of worker threads.

    Raises:
        InfrastructureError: If sentinel signaling fails.
    """
    context = ErrorContext(
        operation="signal_parser_shutdown",
        additional_data={"num_workers": num_workers},
    )

    try:
        logger.info("Sending %s sentinel values to parser workers...", num_workers)
        for _ in range(num_workers):
            file_queue.put(
                Pipeline.SENTINEL,
                timeout=Timeout.PIPELINE_SENTINEL,
            )

        log_operation_success(
            logger=logger,
            operation="signal_parser_shutdown",
            duration_ms=0.0,
            context=context.to_dict(),
        )

    except Exception as e:
        infrastructure_error = InfrastructureError(
            ErrorCode.QUEUE_OPERATION_ERROR,
            f"Failed to signal parser shutdown: {e}",
            context,
            original_error=e,
        )
        log_operation_error(
            logger=logger,
            error=infrastructure_error,
            operation="signal_parser_shutdown",
            context=context.to_dict(),
        )
        raise InfrastructureError(
            ErrorCode.QUEUE_OPERATION_ERROR,
            f"Failed to signal parser shutdown: {e}",
            context,
            original_error=e,
        ) from e


def _wait_for_parser_completion(
    parser_pool: ParserWorkerPool,
    parser_stats: ParserStatistics,
) -> None:
    """Wait for parser pool to complete and log results.

    Args:
        parser_pool: ParserWorkerPool instance.
        parser_stats: ParserStatistics instance.

    Raises:
        InfrastructureError: If parser completion fails.
    """
    context = ErrorContext(
        operation="wait_for_parser_completion",
        additional_data={"items_processed": parser_stats.items_processed},
    )

    try:
        logger.info("Waiting for parser pool to complete...")
        parser_pool.join()
        logger.info(
            "Parser pool completed. Processed %s files.",
            parser_stats.items_processed,
        )

        log_operation_success(
            logger=logger,
            operation="wait_for_parser_completion",
            duration_ms=0.0,
            context=context.to_dict(),
        )

    except Exception as e:
        infrastructure_error = InfrastructureError(
            ErrorCode.PARSER_ERROR,
            f"Parser completion failed: {e}",
            context,
            original_error=e,
        )
        log_operation_error(
            logger=logger,
            error=infrastructure_error,
            operation="wait_for_parser_completion",
            context=context.to_dict(),
        )
        raise InfrastructureError(
            ErrorCode.PARSER_ERROR,
            f"Parser completion failed: {e}",
            context,
            original_error=e,
        ) from e


def _signal_collector_shutdown(
    result_queue: BoundedQueue,
) -> None:
    """Signal collector to shut down.

    Args:
        result_queue: BoundedQueue for results.

    Raises:
        InfrastructureError: If sentinel signaling fails.
    """
    context = ErrorContext(operation="signal_collector_shutdown")

    try:
        logger.info("Sending sentinel value to result collector...")
        result_queue.put(Pipeline.SENTINEL, timeout=Timeout.PIPELINE_SENTINEL)

        log_operation_success(
            logger=logger,
            operation="signal_collector_shutdown",
            duration_ms=0.0,
            context=context.to_dict(),
        )

    except Exception as e:
        infrastructure_error = InfrastructureError(
            ErrorCode.QUEUE_OPERATION_ERROR,
            f"Failed to signal collector shutdown: {e}",
            context,
            original_error=e,
        )
        log_operation_error(
            logger=logger,
            error=infrastructure_error,
            operation="signal_collector_shutdown",
            context=context.to_dict(),
        )
        raise InfrastructureError(
            ErrorCode.QUEUE_OPERATION_ERROR,
            f"Failed to signal collector shutdown: {e}",
            context,
            original_error=e,
        ) from e


def _wait_for_collector_completion(
    collector: ResultCollector,
) -> int:
    """Wait for collector to complete and log results.

    Args:
        collector: ResultCollector instance.

    Returns:
        Number of results collected.

    Raises:
        InfrastructureError: If collector completion fails.
    """
    context = ErrorContext(operation="wait_for_collector_completion")

    try:
        logger.info("Waiting for result collector to complete...")
        collector.join(timeout=Timeout.PIPELINE_SHUTDOWN)

        # Check if collector is still alive after timeout
        if collector.is_alive():
            logger.warning("Collector did not complete within timeout, forcing stop...")
            collector.stop()
            collector.join(timeout=1.0)  # Give it 1 more second to stop gracefully

        result_count = collector.get_result_count()
        logger.info(
            "Result collector completed. Collected %s results.",
            result_count,
        )

        log_operation_success(
            logger=logger,
            operation="wait_for_collector_completion",
            duration_ms=0.0,
            context={**context.to_dict(), "result_count": result_count},
        )

        return result_count

    except Exception as e:
        infrastructure_error = InfrastructureError(
            ErrorCode.COLLECTOR_ERROR,
            f"Collector completion failed: {e}",
            context,
            original_error=e,
        )
        log_operation_error(
            logger=logger,
            error=infrastructure_error,
            operation="wait_for_collector_completion",
            context=context.to_dict(),
        )
        raise InfrastructureError(
            ErrorCode.COLLECTOR_ERROR,
            f"Collector completion failed: {e}",
            context,
            original_error=e,
        ) from e


def _graceful_shutdown(
    scanner: DirectoryScanner,
    parser_pool: ParserWorkerPool,
    collector: ResultCollector,
) -> None:
    """Perform graceful shutdown of pipeline components.

    Args:
        scanner: DirectoryScanner instance.
        parser_pool: ParserWorkerPool instance.
        collector: ResultCollector instance.
    """
    context = ErrorContext(operation="graceful_shutdown")

    try:
        logger.info("Attempting graceful shutdown...")
        scanner.stop()
        parser_pool.stop()
        collector.stop()

        log_operation_success(
            logger=logger,
            operation="graceful_shutdown",
            duration_ms=0.0,
            context=context.to_dict(),
        )

    except Exception as e:
        infrastructure_error = InfrastructureError(
            ErrorCode.PIPELINE_SHUTDOWN_ERROR,
            f"Graceful shutdown failed: {e}",
            context,
            original_error=e,
        )
        log_operation_error(
            logger=logger,
            error=infrastructure_error,
            operation="graceful_shutdown",
            context=context.to_dict(),
        )


def _force_shutdown_if_needed(
    scanner: DirectoryScanner,
    parser_pool: ParserWorkerPool,
    collector: ResultCollector,
) -> None:
    """Force shutdown of components that are still alive.

    Args:
        scanner: DirectoryScanner instance.
        parser_pool: ParserWorkerPool instance.
        collector: ResultCollector instance.
    """
    context = ErrorContext(operation="force_shutdown_if_needed")

    try:
        # Ensure all threads are stopped
        if scanner.is_alive():
            logger.warning("Scanner still alive, forcing stop...")
            scanner.stop()

        if parser_pool.is_alive():
            logger.warning("Parser pool still alive, forcing stop...")
            parser_pool.stop()

        if collector.is_alive():
            logger.warning("Collector still alive, forcing stop...")
            collector.stop()

        log_operation_success(
            logger=logger,
            operation="force_shutdown_if_needed",
            duration_ms=0.0,
            context=context.to_dict(),
        )

    except Exception as e:
        infrastructure_error = InfrastructureError(
            ErrorCode.PIPELINE_SHUTDOWN_ERROR,
            f"Force shutdown failed: {e}",
            context,
            original_error=e,
        )
        log_operation_error(
            logger=logger,
            error=infrastructure_error,
            operation="force_shutdown_if_needed",
            context=context.to_dict(),
        )


def run_pipeline(
    root_path: str,
    extensions: list[str],
    num_workers: int = 4,
    max_queue_size: int = 100,
    cache_path: str | None = None,
) -> list[dict[str, Any]]:
    """Run the complete file processing pipeline.

    This function orchestrates the entire pipeline:
    1. Scanner discovers files and puts them in the file queue
    2. Parser workers consume files, process them, and put results in output queue
    3. ResultCollector gathers all results

    Args:
        root_path: Root directory to scan for files.
        extensions: List of file extensions to scan for (e.g., ['.mp4', '.mkv']).
        num_workers: Number of parser worker threads.
        max_queue_size: Maximum size for bounded queues.
        cache_path: Optional path to cache file for storing scan results.

    Returns:
        List of processed file results.

    Raises:
        InfrastructureError: If pipeline execution fails.
    """
    context = ErrorContext(
        operation="run_pipeline",
        additional_data={
            "root_path": root_path,
            "extensions": extensions,
            "num_workers": num_workers,
            "max_queue_size": max_queue_size,
        },
    )

    logger.info(
        "Starting pipeline: root=%s, extensions=%s, workers=%s",
        root_path,
        extensions,
        num_workers,
    )

    # Record pipeline start time
    start_time = time.time()

    scanner = None
    parser_pool = None
    collector = None

    try:
        # Create pipeline components
        (
            scan_stats,
            queue_stats,
            parser_stats,
            _cache,
            file_queue,
            result_queue,
            scanner,
            parser_pool,
            collector,
        ) = _create_pipeline_components(
            root_path,
            extensions,
            num_workers,
            max_queue_size,
            cache_path,
        )

        # Start all pipeline components
        _start_pipeline_components(scanner, parser_pool, collector, num_workers)

        # Wait for scanner to finish discovering files
        _wait_for_scanner_completion(scanner, scan_stats)

        # Signal parser workers to shut down by sending sentinel values
        _signal_parser_shutdown(file_queue, num_workers)

        # Wait for parser pool to finish processing
        _wait_for_parser_completion(parser_pool, parser_stats)

        # Signal collector to shut down
        _signal_collector_shutdown(result_queue)

        # Wait for collector to finish gathering results
        result_count = _wait_for_collector_completion(collector)

        # Retrieve and return final results
        results = collector.get_results()

        # Calculate total pipeline duration
        total_duration = time.time() - start_time

        # Format and display final statistics
        stats_report = format_statistics(
            scan_stats=scan_stats,
            queue_stats=queue_stats,
            parser_stats=parser_stats,
            total_duration=total_duration,
        )
        logger.info("Pipeline completed successfully!")
        logger.info(stats_report)
        print(stats_report)

        log_operation_success(
            logger=logger,
            operation="run_pipeline",
            duration_ms=total_duration * 1000,
            context={
                **context.to_dict(),
                "total_duration": total_duration,
                "result_count": result_count,
            },
        )

        return results

    except Exception as e:
        infrastructure_error = InfrastructureError(
            ErrorCode.PIPELINE_EXECUTION_ERROR,
            f"Pipeline execution failed: {e}",
            context,
            original_error=e,
        )
        log_operation_error(
            logger=logger,
            error=infrastructure_error,
            operation="run_pipeline",
            context=context.to_dict(),
        )

        # Attempt graceful shutdown
        if scanner and parser_pool and collector:
            _graceful_shutdown(scanner, parser_pool, collector)

        raise InfrastructureError(
            ErrorCode.PIPELINE_EXECUTION_ERROR,
            f"Pipeline execution failed: {e}",
            context,
            original_error=e,
        ) from e

    finally:
        # Ensure all threads are stopped
        if scanner and parser_pool and collector:
            _force_shutdown_if_needed(scanner, parser_pool, collector)
