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
from anivault.shared.constants import APIFields
from anivault.shared.constants.system import EnrichmentStatus, MediaType
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
    enrichment_status: str = APIFields.ENRICHMENT_STATUS_PENDING


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
            enriched.enrichment_status = EnrichmentStatus.SKIPPED
            return enriched

        try:
            # Search for matching media
            if self.tmdb_client is None:
                raise ValueError("TMDB client is not initialized")
            search_results = await self.tmdb_client.search_media(file_info.title)

            if not search_results:
                enriched.enrichment_status = APIFields.ENRICHMENT_STATUS_FAILED
                return enriched

            # Find the best match
            best_match = self._find_best_match(file_info, search_results)

            if best_match is None:
                enriched.enrichment_status = APIFields.ENRICHMENT_STATUS_FAILED
                return enriched

            # Get detailed information if we have a good match
            if best_match["match_confidence"] >= self.min_confidence:
                try:
                    if self.tmdb_client is None:
                        raise ValueError("TMDB client is not initialized")
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
                except (ConnectionError, TimeoutError) as e:
                    # Handle network-related errors
                    error = InfrastructureError(
                        code=ErrorCode.TMDB_API_CONNECTION_ERROR,
                        message=f"Network error during media details retrieval: {e!s}",
                        context=ErrorContext(
                            operation="get_media_details",
                            additional_data={
                                "media_id": best_match["id"],
                                "media_type": best_match["media_type"],
                                "title": file_info.title,
                                "error_type": "network",
                                "original_error": str(e),
                            },
                        ),
                        original_error=e,
                    )
                except (ValueError, KeyError, TypeError) as e:
                    # Handle data processing errors
                    error = DomainError(
                        code=ErrorCode.VALIDATION_ERROR,
                        message=f"Data processing error during media details retrieval: {e!s}",
                        context=ErrorContext(
                            operation="get_media_details",
                            additional_data={
                                "media_id": best_match["id"],
                                "media_type": best_match["media_type"],
                                "title": file_info.title,
                                "error_type": "data_processing",
                                "original_error": str(e),
                            },
                        ),
                        original_error=e,
                    )
                except Exception as e:  # noqa: BLE001
                    # Handle unexpected errors
                    error = InfrastructureError(
                        code=ErrorCode.TMDB_API_REQUEST_FAILED,
                        message=f"Unexpected error during media details retrieval: {e!s}",
                        context=ErrorContext(
                            operation="get_media_details",
                            additional_data={
                                "media_id": best_match["id"],
                                "media_type": best_match["media_type"],
                                "title": file_info.title,
                                "error_type": "unexpected",
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
            enriched.enrichment_status = EnrichmentStatus.SUCCESS

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
            enriched.enrichment_status = EnrichmentStatus.FAILED
        except (ConnectionError, TimeoutError) as e:
            # Handle network-related errors
            error = InfrastructureError(
                code=ErrorCode.TMDB_API_CONNECTION_ERROR,
                message=f"Network error during metadata enrichment: {e!s}",
                context=ErrorContext(
                    operation="enrich_metadata",
                    additional_data={
                        "title": file_info.title,
                        "min_confidence": self.min_confidence,
                        "error_type": "network",
                        "original_error": str(e),
                    },
                ),
                original_error=e,
            )
        except (ValueError, KeyError, TypeError) as e:
            # Handle data processing errors
            error = DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Data processing error during metadata enrichment: {e!s}",
                context=ErrorContext(
                    operation="enrich_metadata",
                    additional_data={
                        "title": file_info.title,
                        "min_confidence": self.min_confidence,
                        "error_type": "data_processing",
                        "original_error": str(e),
                    },
                ),
                original_error=e,
            )
        except Exception as e:  # noqa: BLE001
            # Handle unexpected errors
            error = InfrastructureError(
                code=ErrorCode.TMDB_API_REQUEST_FAILED,
                message=f"Unexpected error during metadata enrichment: {e!s}",
                context=ErrorContext(
                    operation="enrich_metadata",
                    additional_data={
                        "title": file_info.title,
                        "min_confidence": self.min_confidence,
                        "error_type": "unexpected",
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
            enriched.enrichment_status = EnrichmentStatus.FAILED

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
                            message=f"Unexpected error during batch enrichment item {i}: {result!s}",
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
                elif isinstance(result, EnrichedMetadata):
                    enriched_results.append(result)
                else:
                    # Handle unexpected result type
                    failed_result = EnrichedMetadata(file_info=file_infos[i])
                    failed_result.enrichment_status = "failed"
                    enriched_results.append(failed_result)

            log_operation_success(
                logger=logger,
                operation="enrich_batch",
                duration_ms=0,
                additional_context=context.additional_data if context else None,
            )

            return enriched_results

        except (ConnectionError, TimeoutError) as e:
            # Handle network-related errors in batch processing
            error = InfrastructureError(
                code=ErrorCode.TMDB_API_CONNECTION_ERROR,
                message=f"Network error during batch enrichment: {e!s}",
                context=ErrorContext(
                    operation="enrich_batch",
                    additional_data={
                        "file_count": len(file_infos),
                        "min_confidence": self.min_confidence,
                        "error_type": "network",
                        "original_error": str(e),
                    },
                ),
                original_error=e,
            )
        except (ValueError, KeyError, TypeError) as e:
            # Handle data processing errors in batch processing
            error = DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Data processing error during batch enrichment: {e!s}",
                context=ErrorContext(
                    operation="enrich_batch",
                    additional_data={
                        "file_count": len(file_infos),
                        "min_confidence": self.min_confidence,
                        "error_type": "data_processing",
                        "original_error": str(e),
                    },
                ),
                original_error=e,
            )
        except Exception as e:  # noqa: BLE001
            # Handle unexpected errors in batch processing
            error = InfrastructureError(
                code=ErrorCode.TMDB_API_REQUEST_FAILED,
                message=f"Unexpected error during batch enrichment: {e!s}",
                context=ErrorContext(
                    operation="enrich_batch",
                    additional_data={
                        "file_count": len(file_infos),
                        "min_confidence": self.min_confidence,
                        "error_type": "unexpected",
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

        # Validate search results
        if not search_results:
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message="No TMDB search results to match against",
                context=context,
            )

        # Validate file_info (will raise DomainError if invalid)
        if not file_info.title:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="File info has empty title",
                context=context,
            )

        best_match = None
        best_score = 0.0
        failed_results = 0

        for result in search_results:
            try:
                score = self._calculate_match_score(file_info, result)

                if score > best_score:
                    best_score = score
                    best_match = result
                    best_match["match_confidence"] = score

            except DomainError as e:
                # If it's a file_info validation error (empty title), re-raise
                if "title cannot be empty" in str(e.message).lower():
                    raise
                # Otherwise, log and skip this result (partial failure allowed)
                failed_results += 1
                log_operation_error(
                    logger=logger,
                    operation="calculate_match_score",
                    error=e,
                    additional_context={
                        "result_id": result.get("id", "unknown"),
                        "result_title": result.get("title")
                        or result.get("name", "unknown"),
                    },
                )
                continue

        # If all results failed, raise error
        if failed_results == len(search_results):
            raise ApplicationError(
                code=ErrorCode.DATA_PROCESSING_ERROR,
                message=f"All {len(search_results)} TMDB results failed to process",
                context=ErrorContext(
                    operation="find_best_match",
                    additional_data={
                        "title": file_info.title,
                        "failed_count": failed_results,
                        "total_count": len(search_results),
                    },
                ),
            )

        return best_match if best_score >= self.min_confidence else None

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

        Raises:
            DomainError: If validation or data processing fails
        """
        # Validate TMDB result has required fields
        tmdb_title = tmdb_result.get("title") or tmdb_result.get("name")
        if not tmdb_title:
            raise DomainError(
                code=ErrorCode.DATA_PROCESSING_ERROR,
                message="TMDB result missing title/name field",
                context=ErrorContext(
                    operation="calculate_match_score",
                    additional_data={
                        "file_title": file_info.title,
                        "tmdb_keys": list(tmdb_result.keys()),
                    },
                ),
            )

        try:
            score = 0.0

            # Title similarity (most important factor)
            # This will raise DomainError if title validation fails
            title_score = self._calculate_title_similarity(
                file_info.title,
                tmdb_title,
            )
            score += title_score * 0.6

            # Episode/season matching
            try:
                if (
                    file_info.has_episode_info()
                    and tmdb_result.get("media_type") == MediaType.TV
                ):
                    # For TV shows, episode info is relevant
                    score += 0.2
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning(
                    "Data processing error checking episode info: %s. File info: %s",
                    str(e),
                    file_info,
                )
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "Unexpected error checking episode info: %s. File info: %s",
                    str(e),
                    file_info,
                )

            # Season matching
            try:
                if (
                    file_info.has_season_info()
                    and tmdb_result.get("media_type") == MediaType.TV
                ):
                    # For TV shows, season info is relevant
                    score += 0.1
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning(
                    "Data processing error checking season info: %s. File info: %s",
                    str(e),
                    file_info,
                )
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "Unexpected error checking season info: %s. File info: %s",
                    str(e),
                    file_info,
                )

            # Media type bonus
            try:
                if (
                    tmdb_result.get("media_type") == MediaType.TV
                    and file_info.has_episode_info()
                ):
                    score += 0.1
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning(
                    "Data processing error checking media type bonus: %s. File info: %s, TMDB result: %s",
                    str(e),
                    file_info,
                    tmdb_result,
                )
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "Unexpected error checking media type bonus: %s. File info: %s, TMDB result: %s",
                    str(e),
                    file_info,
                    tmdb_result,
                )

            return min(score, 1.0)

        except DomainError:
            # Re-raise DomainError as-is
            raise
        except (ValueError, KeyError, AttributeError, TypeError) as e:
            # Data processing error
            raise DomainError(
                code=ErrorCode.DATA_PROCESSING_ERROR,
                message=f"Data processing error calculating match score: {e}",
                context=ErrorContext(
                    operation="calculate_match_score",
                    additional_data={
                        "file_title": file_info.title,
                        "tmdb_title": tmdb_title,
                        "error_type": type(e).__name__,
                    },
                ),
                original_error=e,
            ) from e
        except Exception as e:
            # Unexpected error
            raise DomainError(
                code=ErrorCode.DATA_PROCESSING_ERROR,
                message=f"Unexpected error calculating match score: {e}",
                context=ErrorContext(
                    operation="calculate_match_score",
                    additional_data={
                        "file_title": file_info.title,
                        "tmdb_title": tmdb_title,
                        "error_type": type(e).__name__,
                    },
                ),
                original_error=e,
            ) from e

    def _calculate_title_similarity(
        self,
        title1: str,
        title2: str,
    ) -> float:
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

        Raises:
            DomainError: If title validation fails or processing errors occur
        """
        # Validate inputs
        if not isinstance(title1, str) or not isinstance(title2, str):
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Title must be a string",
                context=ErrorContext(
                    operation="calculate_title_similarity",
                    additional_data={
                        "title1_type": type(title1).__name__,
                        "title2_type": type(title2).__name__,
                    },
                ),
            )

        if not title1 or not title2:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Title cannot be empty",
                context=ErrorContext(
                    operation="calculate_title_similarity",
                    additional_data={
                        "title1_empty": not title1,
                        "title2_empty": not title2,
                    },
                ),
            )

        try:
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
            words1 = set(t1.split())
            words2 = set(t2.split())

            if not words1 or not words2:
                return 0.0

            intersection = words1.intersection(words2)
            union = words1.union(words2)

            return len(intersection) / len(union) if union else 0.0

        except (ValueError, TypeError, AttributeError) as e:
            # Data processing error
            raise DomainError(
                code=ErrorCode.DATA_PROCESSING_ERROR,
                message=f"Failed to calculate title similarity: {e}",
                context=ErrorContext(
                    operation="calculate_title_similarity",
                    additional_data={
                        "title1": title1[:50],  # Truncate for logging
                        "title2": title2[:50],
                        "error_type": type(e).__name__,
                    },
                ),
                original_error=e,
            ) from e
        except Exception as e:
            # Unexpected error
            raise DomainError(
                code=ErrorCode.DATA_PROCESSING_ERROR,
                message=f"Unexpected error calculating title similarity: {e}",
                context=ErrorContext(
                    operation="calculate_title_similarity",
                    additional_data={
                        "title1": title1[:50],
                        "title2": title2[:50],
                        "error_type": type(e).__name__,
                    },
                ),
                original_error=e,
            ) from e

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
        stats: dict[str, Any] = {
            "min_confidence": self.min_confidence,
            "enable_async": self.enable_async,
        }

        if self.tmdb_client:
            stats["tmdb_client"] = self.tmdb_client.get_stats()

        return stats
