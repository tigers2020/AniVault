"""Metadata enrichment service for anime files.

This module provides a service that enriches parsed anime file metadata
with additional information from the TMDB API, including ratings, genres,
descriptions, and other metadata.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from anivault.core.parser.models import ParsingResult
from anivault.shared.errors import (
    AniVaultError,
    ApplicationError,
    DomainError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
)
from anivault.shared.logging import log_operation_error, log_operation_success

from .tmdb_client import TMDBClient

logger = logging.getLogger(__name__)


@dataclass
class EnrichedMetadata:
    """Enriched metadata combining parsed file info with TMDB data.

    This dataclass combines the original ParsingResult with additional
    metadata fetched from the TMDB API.

    Attributes:
        file_info: Original parsed file information
        tmdb_data: TMDB API response data
        match_confidence: Confidence score for the TMDB match (0.0 to 1.0)
        enrichment_status: Status of the enrichment process
    """

    file_info: ParsingResult
    tmdb_data: dict[str, Any] | None = None
    match_confidence: float = 0.0
    enrichment_status: str = "pending"  # pending, success, failed, skipped


class MetadataEnricher:
    """Service for enriching anime file metadata with TMDB data.

    This service takes parsed anime file information and enriches it with
    additional metadata from the TMDB API, including ratings, genres,
    descriptions, and other relevant information.

    Args:
        tmdb_client: TMDB API client instance
        min_confidence: Minimum confidence threshold for TMDB matches (default: 0.3)
        enable_async: Whether to use async processing (default: True)
    """

    def __init__(
        self,
        tmdb_client: TMDBClient | None = None,
        min_confidence: float = 0.3,
        enable_async: bool = True,
    ):
        """Initialize the metadata enricher.

        Args:
            tmdb_client: TMDB API client instance
            min_confidence: Minimum confidence threshold for TMDB matches
            enable_async: Whether to use async processing
        """
        self.tmdb_client = tmdb_client
        self.min_confidence = min_confidence
        self.enable_async = enable_async

        # Initialize TMDB client if not provided
        if self.tmdb_client is None:
            self.tmdb_client = TMDBClient()

    async def enrich_metadata(self, file_info: ParsingResult) -> EnrichedMetadata:
        """Enrich a single file's metadata with TMDB data.

        This method takes a ParsingResult and attempts to find matching
        media in the TMDB database, then combines the information.

        Args:
            file_info: Parsed file information to enrich

        Returns:
            EnrichedMetadata containing both file info and TMDB data
        """
        context = ErrorContext(
            operation="enrich_metadata",
            additional_data={
                "title": file_info.title,
                "min_confidence": self.min_confidence,
            },
        )

        enriched = EnrichedMetadata(file_info=file_info)

        # Skip if file info is not valid
        if not file_info.is_valid():
            enriched.enrichment_status = "skipped"
            return enriched

        try:
            # Search for matching media
            search_results = await self.tmdb_client.search_media(file_info.title)

            if not search_results:
                enriched.enrichment_status = "failed"
                return enriched

            # Find the best match
            best_match = self._find_best_match(file_info, search_results)

            if best_match is None:
                enriched.enrichment_status = "failed"
                return enriched

            # Get detailed information if we have a good match
            if best_match["match_confidence"] >= self.min_confidence:
                try:
                    details = await self.tmdb_client.get_media_details(
                        best_match["id"],
                        best_match["media_type"],
                    )
                    enriched.tmdb_data = details
                except AniVaultError as e:
                    # Handle AniVault errors from TMDB client
                    log_operation_error(
                        logger=logger,
                        operation="get_media_details",
                        error=e,
                        additional_context=context.additional_data if context else None,
                    )
                    # Fall back to search result if details fail
                    enriched.tmdb_data = best_match
                except Exception as e:
                    # Handle unexpected errors
                    error = InfrastructureError(
                        code=ErrorCode.TMDB_API_REQUEST_FAILED,
                        message=f"Unexpected error during media details retrieval: {str(e)}",
                        context=ErrorContext(
                            operation="get_media_details",
                            additional_data={
                                "media_id": best_match["id"],
                                "media_type": best_match["media_type"],
                                "title": file_info.title,
                                "original_error": str(e),
                            },
                        ),
                        original_error=e,
                    )
                    log_operation_error(
                        logger=logger,
                        operation="get_media_details",
                        error=error,
                        additional_context=context.additional_data if context else None,
                    )
                    # Fall back to search result if details fail
                    enriched.tmdb_data = best_match

            enriched.match_confidence = best_match["match_confidence"]
            enriched.enrichment_status = "success"

            log_operation_success(
                logger=logger,
                operation="enrich_metadata",
                duration_ms=0,
                additional_context=context.additional_data if context else None,
            )

        except AniVaultError as e:
            # Handle AniVault errors from TMDB client
            log_operation_error(
                logger=logger,
                operation="enrich_metadata",
                error=e,
                additional_context=context.additional_data if context else None,
            )
            enriched.enrichment_status = "failed"
        except Exception as e:
            # Handle unexpected errors
            error = InfrastructureError(
                code=ErrorCode.TMDB_API_REQUEST_FAILED,
                message=f"Unexpected error during metadata enrichment: {str(e)}",
                context=ErrorContext(
                    operation="enrich_metadata",
                    additional_data={
                        "title": file_info.title,
                        "min_confidence": self.min_confidence,
                        "original_error": str(e),
                    },
                ),
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="enrich_metadata",
                error=error,
                additional_context=context.additional_data if context else None,
            )
            enriched.enrichment_status = "failed"

        return enriched

    def enrich_metadata_sync(self, file_info: ParsingResult) -> EnrichedMetadata:
        """Synchronous version of enrich_metadata.

        Args:
            file_info: Parsed file information to enrich

        Returns:
            EnrichedMetadata containing both file info and TMDB data
        """
        if self.enable_async:
            return asyncio.run(self.enrich_metadata(file_info))
        # Fallback to sync processing
        return self._enrich_metadata_sync_fallback(file_info)

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
            tasks = [self.enrich_metadata(file_info) for file_info in file_infos]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out exceptions and convert to EnrichedMetadata
            enriched_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # Handle different types of exceptions
                    if isinstance(result, AniVaultError):
                        log_operation_error(
                            logger=logger,
                            operation="enrich_batch_item",
                            error=result,
                            additional_context={
                                "file_index": i,
                                "title": file_infos[i].title,
                            },
                        )
                    else:
                        # Convert unexpected exceptions to InfrastructureError
                        error = InfrastructureError(
                            code=ErrorCode.TMDB_API_REQUEST_FAILED,
                            message=f"Unexpected error during batch enrichment item {i}: {str(result)}",
                            context=ErrorContext(
                                operation="enrich_batch_item",
                                additional_data={
                                    "file_index": i,
                                    "title": file_infos[i].title,
                                    "original_error": str(result),
                                },
                            ),
                            original_error=result,
                        )
                        log_operation_error(
                            logger=logger,
                            operation="enrich_batch_item",
                            error=error,
                            additional_context={
                                "file_index": i,
                                "title": file_infos[i].title,
                            },
                        )

                    # Create failed result
                    failed_result = EnrichedMetadata(file_info=file_infos[i])
                    failed_result.enrichment_status = "failed"
                    enriched_results.append(failed_result)
                else:
                    enriched_results.append(result)

            log_operation_success(
                logger=logger,
                operation="enrich_batch",
                duration_ms=0,
                additional_context=context.additional_data if context else None,
            )

            return enriched_results

        except Exception as e:
            # Handle unexpected errors in batch processing
            error = InfrastructureError(
                code=ErrorCode.TMDB_API_REQUEST_FAILED,
                message=f"Unexpected error during batch enrichment: {str(e)}",
                context=ErrorContext(
                    operation="enrich_batch",
                    additional_data={
                        "file_count": len(file_infos),
                        "min_confidence": self.min_confidence,
                        "original_error": str(e),
                    },
                ),
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="enrich_batch",
                error=error,
                additional_context=context.additional_data if context else None,
            )
            # Return failed results for all files
            failed_results = []
            for file_info in file_infos:
                failed_result = EnrichedMetadata(file_info=file_info)
                failed_result.enrichment_status = "failed"
                failed_results.append(failed_result)
            return failed_results

    def enrich_batch_sync(
        self,
        file_infos: list[ParsingResult],
    ) -> list[EnrichedMetadata]:
        """Synchronous version of enrich_batch.

        Args:
            file_infos: List of parsed file information to enrich

        Returns:
            List of EnrichedMetadata objects
        """
        if self.enable_async:
            return asyncio.run(self.enrich_batch(file_infos))
        # Fallback to sync processing
        return [self.enrich_metadata_sync(file_info) for file_info in file_infos]

    def _find_best_match(
        self,
        file_info: ParsingResult,
        search_results: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Find the best matching media from search results.

        This method implements a scoring algorithm to find the best match
        between the parsed file information and TMDB search results.

        Args:
            file_info: Parsed file information
            search_results: List of TMDB search results

        Returns:
            Best matching result with confidence score, or None if no good match
        """
        context = ErrorContext(
            operation="find_best_match",
            additional_data={
                "title": file_info.title,
                "search_results_count": len(search_results) if search_results else 0,
                "min_confidence": self.min_confidence,
            },
        )

        try:
            if not search_results:
                return None

            best_match = None
            best_score = 0.0

            for result in search_results:
                try:
                    score = self._calculate_match_score(file_info, result)

                    if score > best_score:
                        best_score = score
                        best_match = result
                        best_match["match_confidence"] = score
                except Exception as e:
                    # Log error for individual result scoring but continue processing
                    error = DomainError(
                        code=ErrorCode.VALIDATION_ERROR,
                        message=f"Error calculating match score for result: {str(e)}",
                        context=ErrorContext(
                            operation="calculate_match_score",
                            additional_data={
                                "title": file_info.title,
                                "result_id": result.get("id", "unknown"),
                                "result_title": result.get("title")
                                or result.get("name", "unknown"),
                                "original_error": str(e),
                            },
                        ),
                        original_error=e,
                    )
                    log_operation_error(
                        logger=logger,
                        operation="calculate_match_score",
                        error=error,
                        additional_context=context.additional_data if context else None,
                    )
                    continue

            return best_match if best_score >= self.min_confidence else None

        except Exception as e:
            # Handle unexpected errors in match finding
            error = DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Unexpected error during best match finding: {str(e)}",
                context=ErrorContext(
                    operation="find_best_match",
                    additional_data={
                        "title": file_info.title,
                        "search_results_count": len(search_results)
                        if search_results
                        else 0,
                        "min_confidence": self.min_confidence,
                        "original_error": str(e),
                    },
                ),
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="find_best_match",
                error=error,
                additional_context=context.additional_data if context else None,
            )
            return None

    def _calculate_match_score(
        self,
        file_info: ParsingResult,
        tmdb_result: dict[str, Any],
    ) -> float:
        """Calculate match score between file info and TMDB result.

        This method implements a scoring algorithm that considers:
        - Title similarity
        - Episode/season matching
        - Media type compatibility

        Args:
            file_info: Parsed file information
            tmdb_result: TMDB search result

        Returns:
            Match confidence score (0.0 to 1.0)
        """
        try:
            score = 0.0

            # Title similarity (most important factor)
            try:
                title_score = self._calculate_title_similarity(
                    file_info.title,
                    tmdb_result.get("title") or tmdb_result.get("name", ""),
                )
                score += title_score * 0.6
            except Exception as e:
                # If title similarity calculation fails, log and continue with 0
                logger.warning(
                    "Error calculating title similarity: %s. Title1: %s, Title2: %s",
                    str(e),
                    file_info.title,
                    tmdb_result.get("title") or tmdb_result.get("name", ""),
                )

            # Episode/season matching
            try:
                if (
                    file_info.has_episode_info()
                    and tmdb_result.get("media_type") == "tv"
                ):
                    # For TV shows, episode info is relevant
                    score += 0.2
            except Exception as e:
                logger.warning(
                    "Error checking episode info: %s. File info: %s",
                    str(e),
                    file_info,
                )

            # Season matching
            try:
                if (
                    file_info.has_season_info()
                    and tmdb_result.get("media_type") == "tv"
                ):
                    # For TV shows, season info is relevant
                    score += 0.1
            except Exception as e:
                logger.warning(
                    "Error checking season info: %s. File info: %s",
                    str(e),
                    file_info,
                )

            # Media type bonus
            try:
                if (
                    tmdb_result.get("media_type") == "tv"
                    and file_info.has_episode_info()
                ):
                    score += 0.1
            except Exception as e:
                logger.warning(
                    "Error checking media type bonus: %s. File info: %s, TMDB result: %s",
                    str(e),
                    file_info,
                    tmdb_result,
                )

            return min(score, 1.0)

        except Exception as e:
            # If the entire scoring process fails, return 0
            logger.error(
                "Error calculating match score: %s. File info: %s, TMDB result: %s",
                str(e),
                file_info,
                tmdb_result,
            )
            return 0.0

    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles.

        This method implements a simple similarity algorithm that considers:
        - Exact matches
        - Case-insensitive matches
        - Word overlap

        Args:
            title1: First title
            title2: Second title

        Returns:
            Similarity score (0.0 to 1.0)
        """
        try:
            if not title1 or not title2:
                return 0.0

            # Normalize titles
            t1 = title1.lower().strip()
            t2 = title2.lower().strip()

            # Exact match
            if t1 == t2:
                return 1.0

            # Check if one title contains the other
            if t1 in t2 or t2 in t1:
                return 0.8

            # Word overlap
            try:
                words1 = set(t1.split())
                words2 = set(t2.split())

                if not words1 or not words2:
                    return 0.0

                intersection = words1.intersection(words2)
                union = words1.union(words2)

                return len(intersection) / len(union) if union else 0.0
            except Exception as e:
                logger.warning(
                    "Error calculating word overlap for titles '%s' and '%s': %s",
                    title1,
                    title2,
                    str(e),
                )
                return 0.0

        except Exception as e:
            logger.error(
                "Error calculating title similarity for '%s' and '%s': %s",
                title1,
                title2,
                str(e),
            )
            return 0.0

    def _enrich_metadata_sync_fallback(
        self,
        file_info: ParsingResult,
    ) -> EnrichedMetadata:
        """Fallback sync processing when async is disabled.

        Args:
            file_info: Parsed file information to enrich

        Returns:
            EnrichedMetadata containing both file info and TMDB data
        """
        # This is a simplified sync version
        # In a real implementation, you might want to use threading
        # or other sync approaches
        enriched = EnrichedMetadata(file_info=file_info)
        enriched.enrichment_status = "skipped"  # Skip for now in sync mode
        return enriched

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the enricher and its components.

        Returns:
            Dictionary containing enricher statistics
        """
        stats = {
            "min_confidence": self.min_confidence,
            "enable_async": self.enable_async,
        }

        if self.tmdb_client:
            stats["tmdb_client"] = self.tmdb_client.get_stats()

        return stats
