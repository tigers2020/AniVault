"""TMDB Fetcher module for metadata enrichment.

This module provides a dedicated Fetcher class that encapsulates all TMDB API
interactions, isolating network dependencies and error handling from the core
matching logic.
"""

from __future__ import annotations

import logging
from typing import Any

from anivault.services.tmdb import TMDBClient, TMDBMediaDetails
from anivault.shared.constants import LogContextKeys, LogOperationNames
from anivault.shared.errors import (
    AniVaultError,
    DomainError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
)
from anivault.shared.logging import log_operation_error
from anivault.shared.utils.dataclass_serialization import to_dict

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

    async def search(self, title: str) -> list[dict[str, Any]]:
        """Search for media by title.

        This method wraps TMDBClient.search_media() and converts the
        Pydantic SearchResponse to a list of dictionaries for compatibility
        with existing matching logic.

        Args:
            title: Title to search for

        Returns:
            List of search result dictionaries (empty list if no results)

        Raises:
            InfrastructureError: If network or TMDB API errors occur
            DomainError: If data validation or processing fails

        Example:
            >>> fetcher = TMDBFetcher(tmdb_client)
            >>> results = await fetcher.search("Attack on Titan")
            >>> len(results) > 0
            True
        """
        try:
            # Call TMDB API
            search_response = await self.tmdb_client.search_media(title)

            # Convert dataclass models to dicts
            if not search_response.results:
                return []

            return [to_dict(result) for result in search_response.results]

        except AniVaultError:
            # Re-raise AniVault errors as-is
            raise
        except (ConnectionError, TimeoutError) as e:
            # Network errors → InfrastructureError
            raise InfrastructureError(
                code=ErrorCode.TMDB_API_CONNECTION_ERROR,
                message=f"Network error during TMDB search: {e}",
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
        except Exception as e:
            # Unexpected errors → InfrastructureError
            raise InfrastructureError(
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
        fallback_data: dict[str, Any] | None = None,
    ) -> TMDBMediaDetails | dict[str, Any]:
        """Fetch detailed media information from TMDB.

        This method wraps TMDBClient.get_media_details() and provides
        comprehensive error handling with optional fallback to search results.

        Args:
            tmdb_id: TMDB media ID
            media_type: Media type ('tv' or 'movie')
            fallback_data: Optional fallback data if details fetch fails

        Returns:
            TMDBMediaDetails if successful, or fallback_data if provided

        Raises:
            InfrastructureError: If network or TMDB API errors occur (no fallback)
            DomainError: If data validation or processing fails (no fallback)

        Example:
            >>> fetcher = TMDBFetcher(tmdb_client)
            >>> details = await fetcher.fetch_details(1429, "tv")
            >>> isinstance(details, TMDBMediaDetails)
            True
        """
        try:
            details = await self.tmdb_client.get_media_details(tmdb_id, media_type)
            return self._handle_none_response(
                details, tmdb_id, media_type, fallback_data
            )

        except AniVaultError as e:
            return self._handle_anivault_error(e, tmdb_id, media_type, fallback_data)

        except (ConnectionError, TimeoutError) as e:
            return self._handle_network_error(e, tmdb_id, media_type, fallback_data)

        except (ValueError, KeyError, TypeError) as e:
            return self._handle_data_error(e, tmdb_id, media_type)

        except Exception as e:  # noqa: BLE001
            return self._handle_unexpected_error(e, tmdb_id, media_type, fallback_data)

    def _handle_none_response(
        self,
        details: TMDBMediaDetails | None,
        tmdb_id: int,
        media_type: str,
        fallback_data: dict[str, Any] | None,
    ) -> TMDBMediaDetails | dict[str, Any]:
        """Handle None response from TMDB API."""
        if details is None:
            if fallback_data is not None:
                logger.warning(
                    "TMDB returned None for media details, using fallback (ID: %d, Type: %s)",
                    tmdb_id,
                    media_type,
                )
                return fallback_data

            raise DomainError(
                code=ErrorCode.DATA_PROCESSING_ERROR,
                message=f"TMDB returned None for media ID {tmdb_id}",
                context=ErrorContext(
                    operation=LogOperationNames.GET_MEDIA_DETAILS,
                    additional_data={
                        LogContextKeys.MEDIA_ID: tmdb_id,
                        LogContextKeys.MEDIA_TYPE: media_type,
                    },
                ),
            )

        return details

    def _handle_anivault_error(
        self,
        e: AniVaultError,
        tmdb_id: int,
        media_type: str,
        fallback_data: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Handle AniVaultError with optional fallback."""
        log_operation_error(
            logger=logger,
            operation=LogOperationNames.GET_MEDIA_DETAILS,
            error=e,
            additional_context={
                LogContextKeys.MEDIA_ID: tmdb_id,
                LogContextKeys.MEDIA_TYPE: media_type,
            },
        )

        if fallback_data is not None:
            logger.warning(
                "Using fallback data for media details (ID: %d, Type: %s)",
                tmdb_id,
                media_type,
            )
            return fallback_data

        raise  # noqa: PLE0704

    def _handle_network_error(
        self,
        e: Exception,
        tmdb_id: int,
        media_type: str,
        fallback_data: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Handle network errors (ConnectionError, TimeoutError)."""
        error = InfrastructureError(
            code=ErrorCode.TMDB_API_CONNECTION_ERROR,
            message=f"Network error during media details retrieval: {e}",
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

        if fallback_data is not None:
            logger.warning(
                "Using fallback data after network error (ID: %d, Type: %s)",
                tmdb_id,
                media_type,
            )
            return fallback_data

        raise error from e

    def _handle_data_error(
        self,
        e: Exception,
        tmdb_id: int,
        media_type: str,
    ) -> None:
        """Handle data processing errors (ValueError, KeyError, TypeError)."""
        data_error = DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"Data processing error during media details retrieval: {e}",
            context=ErrorContext(
                operation=LogOperationNames.GET_MEDIA_DETAILS,
                additional_data={
                    LogContextKeys.MEDIA_ID: tmdb_id,
                    LogContextKeys.MEDIA_TYPE: media_type,
                    "error_type": "data_processing",
                    "original_error": str(e),
                },
            ),
            original_error=e,
        )

        logger.exception("Data processing error during media details retrieval")
        raise data_error from e

    def _handle_unexpected_error(
        self,
        e: Exception,
        tmdb_id: int,
        media_type: str,
        fallback_data: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Handle unexpected errors."""
        error = InfrastructureError(
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

        if fallback_data is not None:
            logger.warning(
                "Using fallback data after unexpected error (ID: %d, Type: %s)",
                tmdb_id,
                media_type,
            )
            return fallback_data

        raise error from e


__all__ = ["TMDBFetcher"]
