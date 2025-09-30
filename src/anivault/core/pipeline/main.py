"""Main pipeline orchestrator for AniVault.

This module provides the main entry point for running the complete
file processing pipeline: Scanner → ParserWorkerPool → ResultCollector.
"""

import logging
from pathlib import Path
from typing import Any, Optional
from unittest.mock import Mock

from anivault.core.bounded_queue import BoundedQueue
from anivault.core.pipeline.cache import CacheV1
from anivault.core.pipeline.collector import ResultCollector
from anivault.core.pipeline.parser import ParserWorkerPool
from anivault.core.pipeline.scanner import DirectoryScanner

logger = logging.getLogger(__name__)


# Sentinel object to signal end of processing
class _Sentinel:
    """Sentinel object to signal end of queue processing."""


SENTINEL = _Sentinel()


def run_pipeline(
    root_path: str,
    extensions: list[str],
    num_workers: int = 4,
    max_queue_size: int = 100,
    cache_path: Optional[str] = None,
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
        f"Starting pipeline: root={root_path}, extensions={extensions}, workers={num_workers}",
    )

    # Create a mock statistics object (since Statistics is abstract)
    stats = Mock()
    stats.items_found = 0
    stats.items_processed = 0
    stats.successes = 0
    stats.failures = 0

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
        stats=stats,
        cache_path=cache_path,
    )

    parser_pool = ParserWorkerPool(
        num_workers=num_workers,
        input_queue=file_queue,
        output_queue=result_queue,
        stats=stats,
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

        logger.info(f"Starting parser pool with {num_workers} workers...")
        parser_pool.start()

        logger.info("Starting result collector...")
        collector.start()

        # Wait for scanner to finish discovering files
        logger.info("Waiting for scanner to complete...")
        scanner.join()
        logger.info(f"Scanner completed. Found {stats.items_found} files.")

        # Signal parser workers to shut down by sending sentinel values
        logger.info(f"Sending {num_workers} sentinel values to parser workers...")
        for _ in range(num_workers):
            file_queue.put(SENTINEL, timeout=30.0)

        # Wait for parser pool to finish processing
        logger.info("Waiting for parser pool to complete...")
        parser_pool.join()
        logger.info(f"Parser pool completed. Processed {stats.items_processed} files.")

        # Signal collector to shut down
        logger.info("Sending sentinel value to result collector...")
        result_queue.put(SENTINEL, timeout=30.0)

        # Wait for collector to finish gathering results
        logger.info("Waiting for result collector to complete...")
        collector.join()
        logger.info(
            f"Result collector completed. Collected {collector.get_result_count()} results.",
        )

        # Retrieve and return final results
        results = collector.get_results()

        # Log final statistics
        logger.info("Pipeline completed successfully!")
        logger.info(f"Total files found: {stats.items_found}")
        logger.info(f"Total files processed: {stats.items_processed}")
        logger.info(f"Successful: {stats.successes}")
        logger.info(f"Failed: {stats.failures}")
        logger.info(f"Results collected: {len(results)}")

        return results

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)

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
