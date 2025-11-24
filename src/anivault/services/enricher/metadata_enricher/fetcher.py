"""TMDB Fetcher module for metadata enrichment.

This module provides a dedicated Fetcher class that encapsulates all TMDB API
interactions, isolating network dependencies and error handling from the core
matching logic.
"""

from __future__ import annotations

import logging

from anivault.services.tmdb import TMDBClient, TMDBMediaDetails, TMDBSearchResult
from anivault.shared.constants import LogContextKeys, LogOperationNames
from anivault.shared.errors import (
    AniVaultError,
    AniVaultNetworkError,
    DomainError,
    ErrorCode,
    ErrorContext,
)
from anivault.shared.logging import log_operation_error

logger = logging.getLogger(__name__)


class TMDBFetcher:
    """Fetcher for TMDB API interactions.

    This class encapsulates all TMDB API calls and error handling,
    providing a clean interface for metadata enrichment operations.

    The Fetcher handles:
    - Search requests with automatic result conversion
    - Detail retrieval with comprehensive error handling
    - Network error → InfrastructureError conversion
    - Data processing error → DomainError conversion

    Attributes:
        tmdb_client: TMDB API client instance for making requests
    """

    def __init__(self, tmdb_client: TMDBClient) -> None:
        """Initialize the TMDB Fetcher.

        Args:
            tmdb_client: TMDB API client instance

        Raises:
            ValueError: If tmdb_client is None
        """
        if tmdb_client is None:
            raise ValueError("TMDB client cannot be None")
        self.tmdb_client = tmdb_client

    async def search(self, title: str) -> list[TMDBSearchResult]:
        """Search for media by title.

        This method wraps TMDBClient.search_media() and returns
        type-safe TMDBSearchResult dataclass instances.

        Args:
            title: Title to search for

        Returns:
            List of TMDBSearchResult instances (empty list if no results)

        Raises:
            InfrastructureError: If network or TMDB API errors occur
            DomainError: If data validation or processing fails

        Example:
            >>> fetcher = TMDBFetcher(tmdb_client)
            >>> results = await fetcher.search("Attack on Titan")
            >>> len(results) > 0
            True
            >>> isinstance(results[0], TMDBSearchResult)
            True
        """
        try:
            # Call TMDB API
            search_response = await self.tmdb_client.search_media(title)

            # Return dataclass models directly (type-safe)
            if not search_response.results:
                return []

            return list(search_response.results)

        except AniVaultError:
            # Re-raise AniVault errors as-is
            raise
        except (ConnectionError, TimeoutError) as e:
            # Network errors → AniVaultNetworkError

            if isinstance(e, TimeoutError):
                error_code = ErrorCode.TMDB_API_TIMEOUT
                error_message = f"TMDB search timeout for '{title}': {e}"
            else:
                error_code = ErrorCode.TMDB_API_CONNECTION_ERROR
                error_message = f"Network error during TMDB search: {e}"
            raise AniVaultNetworkError(
                code=error_code,
                message=error_message,
                context=ErrorContext(
                    operation=LogOperationNames.TMDB_SEARCH,
                    additional_data={
                        "title": title,
                        "error_type": "network",
                        LogContextKeys.ORIGINAL_ERROR: str(e),
                    },
                ),
                original_error=e,
            ) from e
        except (ValueError, KeyError, TypeError) as e:
            # Data processing errors → DomainError
            raise DomainError(
                code=ErrorCode.DATA_PROCESSING_ERROR,
                message=f"Data processing error during TMDB search: {e}",
                context=ErrorContext(
                    operation=LogOperationNames.TMDB_SEARCH,
                    additional_data={
                        "title": title,
                        "error_type": "data_processing",
                        "original_error": str(e),
                    },
                ),
                original_error=e,
            ) from e
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Unexpected errors → AniVaultNetworkError

            raise AniVaultNetworkError(
                code=ErrorCode.TMDB_API_REQUEST_FAILED,
                message=f"Unexpected error during TMDB search: {e}",
                context=ErrorContext(
                    operation=LogOperationNames.TMDB_SEARCH,
                    additional_data={
                        "title": title,
                        "error_type": "unexpected",
                        "original_error": str(e),
                    },
                ),
                original_error=e,
            ) from e

    async def fetch_details(
        self,
        tmdb_id: int,
        media_type: str,
    ) -> TMDBMediaDetails | None:
        """Fetch detailed media information from TMDB.

        This method wraps TMDBClient.get_media_details() and provides
        comprehensive error handling.

        Args:
            tmdb_id: TMDB media ID
            media_type: Media type ('tv' or 'movie')

        Returns:
            TMDBMediaDetails if successful, None if not found or error occurs

        Raises:
            InfrastructureError: If network or TMDB API errors occur
            DomainError: If data validation or processing fails

        Example:
            >>> fetcher = TMDBFetcher(tmdb_client)
            >>> details = await fetcher.fetch_details(1429, "tv")
            >>> isinstance(details, TMDBMediaDetails)
            True
        """
        try:
            details = await self.tmdb_client.get_media_details(tmdb_id, media_type)
            return details

        except AniVaultError as e:
            log_operation_error(
                logger=logger,
                operation=LogOperationNames.GET_MEDIA_DETAILS,
                error=e,
                additional_context={
                    LogContextKeys.MEDIA_ID: tmdb_id,
                    LogContextKeys.MEDIA_TYPE: media_type,
                },
            )
            return None

        except (ConnectionError, TimeoutError) as e:
            if isinstance(e, TimeoutError):
                error_code = ErrorCode.TMDB_API_TIMEOUT
                error_message = f"TMDB media details timeout: {e}"
            else:
                error_code = ErrorCode.TMDB_API_CONNECTION_ERROR
                error_message = f"Network error during media details retrieval: {e}"
            error = AniVaultNetworkError(
                code=error_code,
                message=error_message,
                context=ErrorContext(
                    operation=LogOperationNames.GET_MEDIA_DETAILS,
                    additional_data={
                        LogContextKeys.MEDIA_ID: tmdb_id,
                        LogContextKeys.MEDIA_TYPE: media_type,
                        "error_type": "network",
                        LogContextKeys.ORIGINAL_ERROR: str(e),
                    },
                ),
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation=LogOperationNames.GET_MEDIA_DETAILS,
                error=error,
                additional_context={
                    LogContextKeys.MEDIA_ID: tmdb_id,
                    LogContextKeys.MEDIA_TYPE: media_type,
                },
            )
            return None

        except (ValueError, KeyError, TypeError) as e:
            logger.exception(
                "Data processing error during media details retrieval",
                extra={
                    LogContextKeys.MEDIA_ID: tmdb_id,
                    LogContextKeys.MEDIA_TYPE: media_type,
                    "error_type": "data_processing",
                    "original_error": str(e),
                },
            )
            return None

        except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            error = AniVaultNetworkError(
                code=ErrorCode.TMDB_API_REQUEST_FAILED,
                message=f"Unexpected error during media details retrieval: {e}",
                context=ErrorContext(
                    operation=LogOperationNames.GET_MEDIA_DETAILS,
                    additional_data={
                        LogContextKeys.MEDIA_ID: tmdb_id,
                        LogContextKeys.MEDIA_TYPE: media_type,
                        "error_type": "unexpected",
                        "original_error": str(e),
                    },
                ),
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation=LogOperationNames.GET_MEDIA_DETAILS,
                error=error,
                additional_context={
                    LogContextKeys.MEDIA_ID: tmdb_id,
                    LogContextKeys.MEDIA_TYPE: media_type,
                },
            )
            return None


__all__ = ["TMDBFetcher"]
