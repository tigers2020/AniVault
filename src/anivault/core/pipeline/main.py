"""Main pipeline orchestrator for AniVault.

This module provides the main entry point for running the complete
file processing pipeline: Scanner → ParserWorkerPool → ResultCollector.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from anivault.core.bounded_queue import BoundedQueue
from anivault.core.pipeline.cache import CacheV1
from anivault.core.pipeline.collector import ResultCollector
from anivault.core.pipeline.parser import ParserWorkerPool
from anivault.core.pipeline.scanner import DirectoryScanner
from anivault.core.pipeline.utils import (
    ParserStatistics,
    QueueStatistics,
    ScanStatistics,
)

logger = logging.getLogger(__name__)


# Sentinel object to signal end of processing
class _Sentinel:
    """Sentinel object to signal end of queue processing."""


SENTINEL = _Sentinel()


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
    """
    logger.info(
        "Starting pipeline: root=%s, extensions=%s, workers=%s",
        root_path,
        extensions,
        num_workers,
    )

    # Record pipeline start time
    start_time = time.time()

    # Create statistics objects for each component
    scan_stats = ScanStatistics()
    queue_stats = QueueStatistics()
    parser_stats = ParserStatistics()

    # Create cache instance
    cache = CacheV1(cache_dir=Path("cache"))

    # Create bounded queues for inter-component communication
    file_queue = BoundedQueue(capacity=max_queue_size)
    result_queue = BoundedQueue(capacity=max_queue_size)

    # Initialize pipeline components
    scanner = DirectoryScanner(
        root_path=Path(root_path),
        output_queue=file_queue,
        extensions=extensions,
        stats=scan_stats,
        cache_path=cache_path,
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

    try:
        # Start all pipeline components
        logger.info("Starting scanner...")
        scanner.start()

        logger.info("Starting parser pool with %s workers...", num_workers)
        parser_pool.start()

        logger.info("Starting result collector...")
        collector.start()

        # Wait for scanner to finish discovering files
        logger.info("Waiting for scanner to complete...")
        scanner.join()
        logger.info("Scanner completed. Found %s files.", scan_stats.files_scanned)

        # Signal parser workers to shut down by sending sentinel values
        logger.info("Sending %s sentinel values to parser workers...", num_workers)
        for _ in range(num_workers):
            file_queue.put(SENTINEL, timeout=30.0)

        # Wait for parser pool to finish processing
        logger.info("Waiting for parser pool to complete...")
        parser_pool.join()
        logger.info(
            "Parser pool completed. Processed %s files.",
            parser_stats.items_processed,
        )

        # Signal collector to shut down
        logger.info("Sending sentinel value to result collector...")
        result_queue.put(SENTINEL, timeout=30.0)

        # Wait for collector to finish gathering results
        logger.info("Waiting for result collector to complete...")
        collector.join()
        logger.info(
            "Result collector completed. Collected %s results.",
            collector.get_result_count(),
        )

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

        return results

    except Exception:
        logger.exception("Pipeline error")

        # Attempt graceful shutdown
        logger.info("Attempting graceful shutdown...")
        scanner.stop()
        parser_pool.stop()
        collector.stop()

        raise

    finally:
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
