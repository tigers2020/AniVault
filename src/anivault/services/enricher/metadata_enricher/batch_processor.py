"""Batch processing module for concurrent metadata enrichment.

This module provides the BatchProcessor class that handles concurrent
processing of multiple items with semaphore-based concurrency control
and comprehensive error handling.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any

from anivault.core.parser.models import ParsingResult
from anivault.services.enricher.metadata_enricher.models import EnrichedMetadata
from anivault.shared.errors import AniVaultError, ErrorCode, InfrastructureError
from anivault.shared.logging import log_operation_error

logger = logging.getLogger(__name__)


@dataclass
class BatchSummary:
    """Summary of batch processing results.

    Attributes:
        success_count: Number of successfully processed items
        failed_count: Number of failed items
        results: All results (successful and failed EnrichedMetadata objects)

    Example:
        >>> summary = BatchSummary(success_count=8, failed_count=2, results=[...])
        >>> print(f"Success rate: {summary.success_count}/{len(summary.results)}")
    """

    success_count: int
    failed_count: int
    results: list[EnrichedMetadata]


class BatchProcessor:
    """Async batch processor with concurrency control.

    This class handles concurrent processing of multiple items using
    asyncio.gather with semaphore-based concurrency limits. It provides
    comprehensive error handling and result aggregation.

    Attributes:
        concurrency: Maximum number of concurrent workers (default: 5)

    Example:
        >>> processor = BatchProcessor(concurrency=5)
        >>> summary = await processor.process(
        ...     items=file_infos,
        ...     worker=enricher.enrich_metadata
        ... )
        >>> print(f"Processed {summary.success_count} successfully")
    """

    def __init__(self, concurrency: int = 5) -> None:
        """Initialize BatchProcessor with concurrency limit.

        Args:
            concurrency: Maximum number of concurrent workers (default: 5)

        Raises:
            ValueError: If concurrency is less than 1
        """
        if concurrency < 1:
            msg = f"concurrency must be at least 1, got {concurrency}"
            raise ValueError(msg)

        self._concurrency = concurrency
        self._logger = logging.getLogger(__name__)

    async def process(
        self,
        items: Sequence[ParsingResult],
        worker: Callable[[ParsingResult], Awaitable[EnrichedMetadata]],
    ) -> BatchSummary:
        """Process items in parallel with concurrency control.

        This method applies the worker function to each item in parallel,
        respecting the configured concurrency limit. Exceptions are caught
        and converted to failed EnrichedMetadata results.

        Args:
            items: Sequence of items to process
            worker: Async function to apply to each item

        Returns:
            BatchSummary with success/failure counts and all results

        Example:
            >>> async def enrich_item(item: ParsingResult) -> EnrichedMetadata:
            ...     # ... enrichment logic ...
            ...     return enriched
            >>> summary = await processor.process(items, enrich_item)
        """
        if not items:
            return BatchSummary(success_count=0, failed_count=0, results=[])

        semaphore = asyncio.Semaphore(self._concurrency)

        async def wrapped(item: ParsingResult) -> EnrichedMetadata:
            """Wrap worker with semaphore for concurrency control."""
            async with semaphore:
                return await worker(item)

        # Execute all tasks concurrently with exception handling
        results = await asyncio.gather(
            *(wrapped(item) for item in items),
            return_exceptions=True,
        )

        return self._build_summary(items, results)

    def _build_summary(
        self,
        items: Sequence[ParsingResult],
        results: Sequence[Any],
    ) -> BatchSummary:
        """Build summary from results, handling exceptions.

        Args:
            items: Original input items
            results: Results from asyncio.gather (may include exceptions)

        Returns:
            BatchSummary with success/failure counts and results
        """
        # pylint: disable=import-outside-toplevel,redefined-outer-name,reimported
        # Lazy import to avoid circular dependency
        from anivault.services.enricher.metadata_enricher.models import EnrichedMetadata

        enriched_results: list[EnrichedMetadata] = []
        success_count = 0
        failed_count = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Log error with context
                self._log_error(result, items[i], i)

                # Create failed result
                failed_result = EnrichedMetadata(file_info=items[i])
                failed_result.enrichment_status = "failed"
                enriched_results.append(failed_result)
                failed_count += 1

            elif isinstance(result, EnrichedMetadata):
                # Successful result
                enriched_results.append(result)
                success_count += 1

            else:
                # Unexpected result type
                self._logger.warning(
                    "Unexpected result type in batch processing",
                    extra={
                        "file_index": i,
                        "title": items[i].title,
                        "result_type": type(result).__name__,
                    },
                )
                failed_result = EnrichedMetadata(file_info=items[i])
                failed_result.enrichment_status = "failed"
                enriched_results.append(failed_result)
                failed_count += 1

        return BatchSummary(
            success_count=success_count,
            failed_count=failed_count,
            results=enriched_results,
        )

    def _log_error(
        self,
        error: Exception,
        item: ParsingResult,
        index: int,
    ) -> None:
        """Log error with appropriate context.

        Args:
            error: The exception that occurred
            item: The item being processed
            index: Index of the item in the batch
        """
        if isinstance(error, AniVaultError):
            # AniVault errors already have context
            log_operation_error(
                logger=self._logger,
                operation="batch_process_item",
                error=error,
                additional_context={
                    "file_index": index,
                    "title": item.title,
                },
            )
        else:
            # Convert unexpected exceptions to InfrastructureError
            wrapped_error = InfrastructureError(
                code=ErrorCode.TMDB_API_REQUEST_FAILED,
                message=f"Unexpected error during batch processing item {index}: {error!s}",
                context=None,
                original_error=error,
            )
            log_operation_error(
                logger=self._logger,
                operation="batch_process_item",
                error=wrapped_error,
                additional_context={
                    "file_index": index,
                    "title": item.title,
                    "original_error": str(error),
                },
            )


__all__ = ["BatchProcessor", "BatchSummary"]
