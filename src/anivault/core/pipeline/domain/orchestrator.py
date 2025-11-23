"""Pipeline orchestration and component factory.

This module provides factory classes and orchestration functions for the pipeline:
- PipelineFactory: Creates and wires up all pipeline components
- run_pipeline: Main orchestration function for running the complete pipeline
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from anivault.core.constants import ProcessStatus
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
from anivault.shared.errors import ErrorCode, ErrorContext, InfrastructureError
from anivault.shared.logging import log_operation_error, log_operation_success
from anivault.shared.metadata_models import FileMetadata

logger = logging.getLogger(__name__)


def _file_metadata_to_dict(metadata: FileMetadata) -> dict[str, Any]:
    """Convert FileMetadata to dictionary for backward compatibility.

    This function converts FileMetadata instances back to dictionary format
    to maintain compatibility with existing code that expects dict structures.

    Args:
        metadata: FileMetadata instance to convert

    Returns:
        Dictionary representation of FileMetadata
    """
    return {
        "file_path": str(metadata.file_path),
        "file_name": metadata.file_name,
        "title": metadata.title,
        "file_type": metadata.file_type,
        "file_extension": f".{metadata.file_type}",
        "year": metadata.year,
        "season": metadata.season,
        "episode": metadata.episode,
        "genres": metadata.genres,
        "overview": metadata.overview,
        "poster_path": metadata.poster_path,
        "vote_average": metadata.vote_average,
        "tmdb_id": metadata.tmdb_id,
        "media_type": metadata.media_type,
        "status": ProcessStatus.SUCCESS.value,  # All FileMetadata are considered successful
    }


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
        context = ErrorContext(
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
        components = _create_pipeline_components(
            root_path, extensions, num_workers, max_queue_size, cache_path
        )
        scanner, parser_pool, collector = (
            components["scanner"],
            components["parser_pool"],
            components["collector"],
        )

        _execute_pipeline(components, num_workers)
        results = _collect_results(components, start_time, context)

        return results

    except Exception as e:  # noqa: BLE001
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
) -> dict[str, Any]:
    """Create pipeline components."""
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

    return {
        "scan_stats": scan_stats,
        "queue_stats": queue_stats,
        "parser_stats": parser_stats,
        "file_queue": file_queue,
        "result_queue": result_queue,
        "scanner": scanner,
        "parser_pool": parser_pool,
        "collector": collector,
    }


def _execute_pipeline(components: dict[str, Any], num_workers: int) -> None:
    """Execute pipeline stages."""
    scanner = components["scanner"]
    parser_pool = components["parser_pool"]
    collector = components["collector"]
    file_queue = components["file_queue"]
    result_queue = components["result_queue"]
    scan_stats = components["scan_stats"]
    parser_stats = components["parser_stats"]

    start_pipeline_components(scanner, parser_pool, collector, num_workers)
    wait_for_scanner_completion(scanner, scan_stats)
    signal_parser_shutdown(file_queue, num_workers)
    wait_for_parser_completion(parser_pool, parser_stats)
    signal_collector_shutdown(result_queue)
    wait_for_collector_completion(collector)


def _collect_results(
    components: dict[str, Any],
    start_time: float,
    context: ErrorContext,
) -> list[dict[str, Any]]:
    """Collect results and log statistics."""
    collector = components["collector"]
    scan_stats = components["scan_stats"]
    queue_stats = components["queue_stats"]
    parser_stats = components["parser_stats"]

    result_count = wait_for_collector_completion(collector)
    file_metadata_results = collector.get_results()
    total_duration = time.time() - start_time

    # Convert FileMetadata to dict for backward compatibility
    results = [_file_metadata_to_dict(metadata) for metadata in file_metadata_results]

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
            **context.safe_dict(),
            "total_duration": total_duration,
            "result_count": result_count,
        },
    )

    return results


def _handle_pipeline_error(
    e: Exception,
    context: ErrorContext,
    scanner: Any,
    parser_pool: Any,
    collector: Any,
) -> None:
    """Handle pipeline execution errors."""
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

    raise InfrastructureError(
        ErrorCode.PIPELINE_EXECUTION_ERROR,
        f"Pipeline execution failed: {e}",
        context,
        original_error=e,
    ) from e
