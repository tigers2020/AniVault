"""Pipeline component lifecycle management.

This module provides functions for managing the lifecycle of pipeline components:
- Starting components
- Waiting for completion
- Signaling shutdown
- Graceful and forced shutdown procedures
"""

from __future__ import annotations

import logging

from anivault.core.pipeline.components import (
    DirectoryScanner,
    ParserWorkerPool,
    ResultCollector,
)
from anivault.core.pipeline.utils import (
    BoundedQueue,
    ParserStatistics,
    ScanStatistics,
)
from anivault.shared.constants import Pipeline, Timeout
from anivault.shared.constants.network import NetworkConfig
from anivault.shared.errors import ErrorCode, ErrorContext, InfrastructureError
from anivault.shared.logging import log_operation_error, log_operation_success

logger = logging.getLogger(__name__)


def start_pipeline_components(
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
            context=context.safe_dict(),
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
            context=context.safe_dict(),
        )
        raise InfrastructureError(
            ErrorCode.PIPELINE_EXECUTION_ERROR,
            f"Failed to start pipeline components: {e}",
            context,
            original_error=e,
        ) from e


def wait_for_scanner_completion(
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
            context=context.safe_dict(),
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
            context=context.safe_dict(),
        )
        raise InfrastructureError(
            ErrorCode.SCANNER_ERROR,
            f"Scanner completion failed: {e}",
            context,
            original_error=e,
        ) from e


def signal_parser_shutdown(
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
            context=context.safe_dict(),
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
            context=context.safe_dict(),
        )
        raise InfrastructureError(
            ErrorCode.QUEUE_OPERATION_ERROR,
            f"Failed to signal parser shutdown: {e}",
            context,
            original_error=e,
        ) from e


def wait_for_parser_completion(
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
            context=context.safe_dict(),
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
            context=context.safe_dict(),
        )
        raise InfrastructureError(
            ErrorCode.PARSER_ERROR,
            f"Parser completion failed: {e}",
            context,
            original_error=e,
        ) from e


def signal_collector_shutdown(
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
            context=context.safe_dict(),
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
            context=context.safe_dict(),
        )
        raise InfrastructureError(
            ErrorCode.QUEUE_OPERATION_ERROR,
            f"Failed to signal collector shutdown: {e}",
            context,
            original_error=e,
        ) from e


def wait_for_collector_completion(
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
            collector.join(
                timeout=NetworkConfig.DEFAULT_TIMEOUT,
            )  # Give it 1 more second to stop gracefully

        result_count = collector.get_result_count()
        logger.info(
            "Result collector completed. Collected %s results.",
            result_count,
        )

        log_operation_success(
            logger=logger,
            operation="wait_for_collector_completion",
            duration_ms=0.0,
            context={**context.safe_dict(), "result_count": result_count},
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
            context=context.safe_dict(),
        )
        raise InfrastructureError(
            ErrorCode.COLLECTOR_ERROR,
            f"Collector completion failed: {e}",
            context,
            original_error=e,
        ) from e


def graceful_shutdown(
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
            context=context.safe_dict(),
        )

    except Exception as e:  # noqa: BLE001
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
            context=context.safe_dict(),
        )


def force_shutdown_if_needed(
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
            context=context.safe_dict(),
        )

    except Exception as e:  # noqa: BLE001
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
            context=context.safe_dict(),
        )
