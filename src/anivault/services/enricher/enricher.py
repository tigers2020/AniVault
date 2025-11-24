"""Metadata enrichment service for anime files.

This module provides a service that enriches parsed anime file metadata
with additional information from the TMDB API, including ratings, genres,
descriptions, and other metadata.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from anivault.core.constants import ProcessingThresholds
from anivault.core.parser.models import ParsingResult
from anivault.services.tmdb import ScoredSearchResult, TMDBClient, TMDBSearchResult
from anivault.shared.constants import APIFields
from anivault.shared.constants.system import EnrichmentStatus
from anivault.shared.errors import (
    AniVaultError,
    ApplicationError,
    DomainError,
    ErrorCode,
    ErrorContext,
)
from anivault.shared.logging import log_operation_error, log_operation_success

from .metadata_enricher.batch_processor import BatchProcessor
from .metadata_enricher.fetcher import TMDBFetcher
from .metadata_enricher.models import EnrichedMetadata
from .metadata_enricher.scoring import ScoringEngine, create_default_scoring_engine

logger = logging.getLogger(__name__)


class MetadataEnricher:
    """Service for enriching anime file metadata with TMDB data."""

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        tmdb_client: TMDBClient | None = None,
        min_confidence: float = ProcessingThresholds.MIN_ENRICHMENT_CONFIDENCE,
        scoring_engine: ScoringEngine | None = None,
        fetcher: TMDBFetcher | None = None,
        batch_processor: BatchProcessor | None = None,
        batch_concurrency: int = 5,
    ):
        """Initialize the metadata enricher."""
        self.tmdb_client = tmdb_client if tmdb_client is not None else TMDBClient()
        self.min_confidence = min_confidence
        self.scoring_engine = scoring_engine if scoring_engine is not None else create_default_scoring_engine()
        self.fetcher = fetcher if fetcher is not None else TMDBFetcher(self.tmdb_client)
        self.batch_processor = batch_processor if batch_processor is not None else BatchProcessor(concurrency=batch_concurrency)

    async def enrich_metadata(self, file_info: ParsingResult) -> EnrichedMetadata:
        """Enrich file metadata with TMDB data."""
        enriched = EnrichedMetadata(file_info=file_info)

        if not file_info.is_valid():
            enriched.enrichment_status = EnrichmentStatus.SKIPPED
            return enriched

        try:
            # Search and find best match
            search_results = await self.fetcher.search(file_info.title)
            if not search_results:
                enriched.enrichment_status = APIFields.ENRICHMENT_STATUS_FAILED
                return enriched

            best_match = self._find_best_match(file_info, search_results)
            if not best_match:
                enriched.enrichment_status = APIFields.ENRICHMENT_STATUS_FAILED
                return enriched

            # Fetch details if confidence is sufficient
            if best_match.confidence_score >= self.min_confidence:
                details = await self.fetcher.fetch_details(
                    best_match.id,
                    best_match.media_type,
                )
                enriched.tmdb_data = details

            enriched.match_confidence = best_match.confidence_score
            enriched.enrichment_status = EnrichmentStatus.SUCCESS

        except AniVaultError as e:
            # Handle known errors (Fetcher already logged)
            log_operation_error(logger=logger, operation="enrich_metadata", error=e)
            enriched.enrichment_status = EnrichmentStatus.FAILED
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            # Wrap data processing errors
            error = ApplicationError(
                code=ErrorCode.DATA_PROCESSING_ERROR,
                message=f"Enrichment failed: {e}",
                original_error=e,
            )
            log_operation_error(logger=logger, operation="enrich_metadata", error=error)
            enriched.enrichment_status = EnrichmentStatus.FAILED

        return enriched

    def enrich_metadata_sync(self, file_info: ParsingResult) -> EnrichedMetadata:
        """Synchronous version of enrich_metadata."""
        return asyncio.run(self.enrich_metadata(file_info))

    async def enrich_batch(
        self,
        file_infos: list[ParsingResult],
    ) -> list[EnrichedMetadata]:
        """Enrich multiple files' metadata in batch.

        This method processes multiple files concurrently, respecting
        rate limits and concurrency controls.

        Args:
            file_infos: List of parsed file information to enrich

        Returns:
            List of EnrichedMetadata objects
        """
        context = ErrorContext(
            operation="enrich_batch",
            additional_data={
                "file_count": len(file_infos),
                "min_confidence": self.min_confidence,
            },
        )

        try:
            # Use BatchProcessor for concurrent processing (handles all errors)
            summary = await self.batch_processor.process(
                items=file_infos,
                worker=self.enrich_metadata,
            )

            # Log success with statistics
            log_operation_success(
                logger=logger,
                operation="enrich_batch",
                duration_ms=0,
                additional_context={
                    "success_count": summary.success_count,
                    "failed_count": summary.failed_count,
                    "total_count": len(file_infos),
                },
            )

            return summary.results

        except AniVaultError:
            # Re-raise our own errors (already logged by BatchProcessor)
            raise
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Wrap unexpected errors
            error = ApplicationError(
                code=ErrorCode.DATA_PROCESSING_ERROR,
                message=f"Batch enrichment failed: {e}",
                context=context,
                original_error=e,
            )
            log_operation_error(logger=logger, operation="enrich_batch", error=error)
            raise error from e

    def enrich_batch_sync(
        self,
        file_infos: list[ParsingResult],
    ) -> list[EnrichedMetadata]:
        """Synchronous version of enrich_batch."""
        return asyncio.run(self.enrich_batch(file_infos))

    def _find_best_match(
        self,
        file_info: ParsingResult,
        search_results: list[TMDBSearchResult],
    ) -> ScoredSearchResult | None:
        """Find best matching media from search results.

        Args:
            file_info: Parsed file information
            search_results: List of TMDB search results

        Returns:
            ScoredSearchResult with highest confidence score, or None if no match
        """
        if not search_results:
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message="No TMDB search results to match against",
            )

        best_match: ScoredSearchResult | None = None
        best_score = 0.0

        for result in search_results:
            try:
                score = self._calculate_match_score(file_info, result)
                if score > best_score:
                    best_score = score
                    # Create ScoredSearchResult with confidence score
                    best_match = ScoredSearchResult(
                        id=result.id,
                        media_type=result.media_type,
                        title=result.title,
                        name=result.name,
                        original_title=result.original_title,
                        original_name=result.original_name,
                        release_date=result.release_date,
                        first_air_date=result.first_air_date,
                        popularity=result.popularity,
                        vote_average=result.vote_average,
                        vote_count=result.vote_count,
                        overview=result.overview,
                        original_language=result.original_language,
                        poster_path=result.poster_path,
                        backdrop_path=result.backdrop_path,
                        genre_ids=result.genre_ids,
                        confidence_score=score,
                    )
            except DomainError:
                # Skip invalid results (ScoringEngine already logged)
                continue

        return best_match if best_score >= self.min_confidence else None

    def _calculate_match_score(
        self,
        file_info: ParsingResult,
        tmdb_result: TMDBSearchResult,
    ) -> float:
        """Calculate match score between file info and TMDB result.

        Delegates to ScoringEngine for composite scoring.

        Args:
            file_info: Parsed file information
            tmdb_result: TMDB search result dataclass instance

        Returns:
            Match confidence score (0.0 to 1.0)
        """
        # Delegate to ScoringEngine (handles all validation and errors)
        score, _evidence = self.scoring_engine.calculate_score(file_info, tmdb_result)
        return score

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the enricher and its components."""
        return {
            "min_confidence": self.min_confidence,
            "tmdb_client": self.tmdb_client.get_stats() if self.tmdb_client else None,
        }
