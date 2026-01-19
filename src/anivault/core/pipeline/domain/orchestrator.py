"""Pipeline orchestration and component factory.

This module provides factory classes and orchestration functions for the pipeline:
- PipelineFactory: Creates and wires up all pipeline components
- run_pipeline: Main orchestration function for running the complete pipeline
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from anivault.core.pipeline.components import (
    CacheV1,
    DirectoryScanner,
    ParserWorkerPool,
    ResultCollector,
)
from anivault.core.pipeline.domain.lifecycle import (
    force_shutdown_if_needed,
    graceful_shutdown,
    signal_collector_shutdown,
    signal_parser_shutdown,
    start_pipeline_components,
    wait_for_collector_completion,
    wait_for_parser_completion,
    wait_for_scanner_completion,
)
from anivault.core.pipeline.domain.statistics import format_statistics
from anivault.core.pipeline.utils import (
    BoundedQueue,
    ParserStatistics,
    QueueStatistics,
    ScanStatistics,
)
from anivault.shared.constants import ProcessingConfig
from anivault.shared.errors import ErrorCode, ErrorContextModel, InfrastructureError
from anivault.shared.logging import log_operation_error, log_operation_success
from anivault.shared.models.metadata import FileMetadata

logger = logging.getLogger(__name__)


@dataclass
class PipelineComponents:
    """Container for all pipeline components.

    This dataclass provides type-safe access to pipeline components,
    replacing the previous dict-based approach.
    """

    scan_stats: ScanStatistics
    queue_stats: QueueStatistics
    parser_stats: ParserStatistics
    file_queue: BoundedQueue
    result_queue: BoundedQueue
    scanner: DirectoryScanner
    parser_pool: ParserWorkerPool
    collector: ResultCollector


class PipelineFactory:
    """Factory for creating and initializing pipeline components.

    This class provides methods for creating all necessary pipeline components
    with proper initialization and wiring.
    """

    @staticmethod
    def create_components(
        root_path: str,
        extensions: list[str],
        num_workers: int,
        max_queue_size: int,
        _cache_path: str | None = None,
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
            _cache_path: Optional path to cache file (currently unused).

        Returns:
            Tuple containing all pipeline components:
            - scan_stats: Statistics for directory scanning
            - queue_stats: Statistics for queue operations
            - parser_stats: Statistics for parser operations
            - cache: Cache instance for storing results
            - file_queue: Queue for files to be parsed
            - result_queue: Queue for parsing results
            - scanner: Directory scanner instance
            - parser_pool: Parser worker pool instance
            - collector: Result collector instance

        Raises:
            InfrastructureError: If component initialization fails.
        """
        context = ErrorContextModel(
            operation="create_pipeline_components",
            additional_data={
                "root_path": root_path,
                "extensions_count": len(extensions),
                "num_workers": num_workers,
                "max_queue_size": max_queue_size,
            },
        )

        try:
            # Create statistics objects for each component
            scan_stats = ScanStatistics()
            queue_stats = QueueStatistics()
            parser_stats = ParserStatistics()

            # Create cache instance (uses SQLite, cache_dir is optional)
            cache = CacheV1(cache_dir=None)  # Uses project root / cache by default

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
                context=context.safe_dict(),
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

        # pylint: disable-next=broad-exception-caught

        # pylint: disable-next=broad-exception-caught

        except Exception as e:  # pylint: disable=broad-exception-caught
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
                context=context.safe_dict(),
            )
            raise InfrastructureError(
                ErrorCode.PIPELINE_INITIALIZATION_ERROR,
                f"Failed to create pipeline components: {e}",
                context,
                original_error=e,
            ) from e


def run_pipeline(
    root_path: str,
    extensions: list[str],
    num_workers: int = ProcessingConfig.MAX_PROCESSING_WORKERS,
    max_queue_size: int = ProcessingConfig.DEFAULT_QUEUE_SIZE,
    cache_path: str | None = None,
) -> list[FileMetadata]:
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
        List of FileMetadata instances.

    Raises:
        InfrastructureError: If pipeline execution fails.
    """
    context = ErrorContextModel(
        operation="run_pipeline",
        additional_data={
            "root_path": root_path,
            "extensions_count": len(extensions),
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

    start_time = time.time()
    scanner = None
    parser_pool = None
    collector = None

    try:
        components = _create_pipeline_components(root_path, extensions, num_workers, max_queue_size, cache_path)
        scanner = components.scanner
        parser_pool = components.parser_pool
        collector = components.collector

        _execute_pipeline(components, num_workers)
        results = _collect_results(components, start_time, context)

        return results

    # pylint: disable-next=broad-exception-caught

    # pylint: disable-next=broad-exception-caught

    except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught
        _handle_pipeline_error(e, context, scanner, parser_pool, collector)
        # _handle_pipeline_error raises InfrastructureError, so this is unreachable
        # but mypy needs an explicit return
        return []

    finally:
        if scanner and parser_pool and collector:
            force_shutdown_if_needed(scanner, parser_pool, collector)


def _create_pipeline_components(
    root_path: str,
    extensions: list[str],
    num_workers: int,
    max_queue_size: int,
    cache_path: str | None,
) -> PipelineComponents:
    """Create pipeline components with type-safe structure.

    Args:
        root_path: Root directory to scan
        extensions: File extensions to scan
        num_workers: Number of parser workers
        max_queue_size: Maximum queue size
        cache_path: Optional cache path

    Returns:
        PipelineComponents dataclass with all components
    """
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
    ) = PipelineFactory.create_components(
        root_path=root_path,
        extensions=extensions,
        num_workers=num_workers,
        max_queue_size=max_queue_size,
        _cache_path=cache_path,
    )

    return PipelineComponents(
        scan_stats=scan_stats,
        queue_stats=queue_stats,
        parser_stats=parser_stats,
        file_queue=file_queue,
        result_queue=result_queue,
        scanner=scanner,
        parser_pool=parser_pool,
        collector=collector,
    )


def _execute_pipeline(components: PipelineComponents, num_workers: int) -> None:
    """Execute pipeline stages.

    Args:
        components: Pipeline components container
        num_workers: Number of parser workers
    """
    start_pipeline_components(components.scanner, components.parser_pool, components.collector, num_workers)
    wait_for_scanner_completion(components.scanner, components.scan_stats)
    signal_parser_shutdown(components.file_queue, num_workers)
    wait_for_parser_completion(components.parser_pool, components.parser_stats)
    signal_collector_shutdown(components.result_queue)
    wait_for_collector_completion(components.collector)


def _collect_results(
    components: PipelineComponents,
    start_time: float,
    context: ErrorContextModel,
) -> list[FileMetadata]:
    """Collect results and log statistics.

    Args:
        components: Pipeline components container
        start_time: Pipeline start time
        context: Error context for logging

    Returns:
        List of processed file results as FileMetadata
    """
    result_count = wait_for_collector_completion(components.collector)
    file_metadata_results = components.collector.get_results()
    total_duration = time.time() - start_time

    stats_report = format_statistics(
        scan_stats=components.scan_stats,
        queue_stats=components.queue_stats,
        parser_stats=components.parser_stats,
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
            **context.safe_dict(),
            "total_duration": total_duration,
            "result_count": result_count,
        },
    )

    return file_metadata_results


def _handle_pipeline_error(
    e: Exception,
    context: ErrorContextModel,
    scanner: DirectoryScanner | None,
    parser_pool: ParserWorkerPool | None,
    collector: ResultCollector | None,
) -> None:
    """Handle pipeline execution errors with consistent error handling.

    Args:
        e: Exception that occurred
        context: Error context for logging
        scanner: Scanner instance or None
        parser_pool: Parser pool instance or None
        collector: Collector instance or None
    """
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
        context=context.safe_dict(),
    )

    if scanner and parser_pool and collector:
        graceful_shutdown(scanner, parser_pool, collector)

    raise infrastructure_error from e
