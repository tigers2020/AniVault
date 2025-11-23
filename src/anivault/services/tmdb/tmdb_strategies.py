"""TMDB Search Strategy Pattern Implementation.

This module implements the Strategy pattern for TMDB search operations,
supporting both TV show and movie searches with a common interface.

Design:
- SearchStrategy (ABC): Abstract base class defining search interface
- TvSearchStrategy: Concrete strategy for TV show searches
- MovieSearchStrategy: Concrete strategy for movie searches

The strategy pattern allows the TMDB client to switch between TV and movie
searches without changing the client code.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Literal, cast

from anivault.services.tmdb.tmdb_models import (
    TMDBMediaDetails,
    TMDBSearchResult,
)
from anivault.shared.errors import (
    AniVaultNetworkError,
    ErrorCode,
    ErrorContext,
)
from anivault.shared.utils.dataclass_serialization import from_dict

logger = logging.getLogger(__name__)


class SearchStrategy(ABC):
    """Abstract base class for TMDB search strategies.

    This class defines the common interface for all search strategies.
    Concrete implementations handle TV show or movie searches.

    Subclasses must implement:
        - get_media_type(): Return "tv" or "movie"
        - _to_search_result(): Convert raw API result to TMDBSearchResult
        - _to_details_model(): Convert raw API result to TMDBMediaDetails
    """

    @abstractmethod
    def get_media_type(self) -> Literal["tv", "movie"]:
        """Get the media type this strategy handles."""
        ...

    @abstractmethod
    async def search(self, title: str) -> list[TMDBSearchResult]:
        """Search for media using this strategy.

        Args:
            title: Title to search for

        Returns:
            List of search results
        """
        ...

    def _to_search_result(self, raw_result: Any) -> TMDBSearchResult:
        """Convert raw API result to TMDBSearchResult model.

        Converts raw API response using from_dict,
        which handles dict, dict-like objects, and objects with __dict__.

        Args:
            raw_result: Raw result from TMDB API (dict or dict-like object)

        Returns:
            TMDBSearchResult dataclass

        Raises:
            TypeError: If result data doesn't match TMDBSearchResult schema

        Note:
            BaseDataclass (via extra="ignore") gracefully handles unknown fields
            from TMDB API, so no manual normalization is needed.
        """
        # Convert to dict if needed
        if isinstance(raw_result, dict):
            data = raw_result
        elif hasattr(raw_result, "__dict__"):
            data = {
                k: v for k, v in raw_result.__dict__.items() if not k.startswith("_")
            }
        elif hasattr(raw_result, "get"):
            data = dict(raw_result)
        else:
            # Fallback for unexpected types
            logger.warning(
                "Unexpected result type: %s, creating minimal fallback",
                type(raw_result),
            )
            media_type = self.get_media_type()
            data = {
                "id": 0,
                "media_type": media_type,
                "name" if media_type == "tv" else "title": str(raw_result),
            }

        # Add media_type field
        data["media_type"] = self.get_media_type()

        # Convert to dataclass using from_dict (extra='ignore' handles unknown fields)
        return cast("TMDBSearchResult", from_dict(TMDBSearchResult, data))

    def _to_details_model(self, raw_result: Any) -> TMDBMediaDetails | None:
        """Convert raw API result to TMDBMediaDetails model.

        Converts raw API response using from_dict.

        Args:
            raw_result: Raw details result from TMDB API

        Returns:
            TMDBMediaDetails dataclass or None if validation fails
        """
        try:
            # Convert to dict if needed
            if isinstance(raw_result, dict):
                data = raw_result
            elif hasattr(raw_result, "__dict__"):
                data = {
                    k: v
                    for k, v in raw_result.__dict__.items()
                    if not k.startswith("_")
                }
            elif hasattr(raw_result, "get"):
                data = dict(raw_result)
            else:
                logger.warning(
                    "Unexpected details type: %s",
                    type(raw_result),
                )
                return None

            # Convert to dataclass using from_dict
            return cast("TMDBMediaDetails", from_dict(TMDBMediaDetails, data))

        except (TypeError, KeyError) as e:
            logger.exception(
                "Failed to parse media details into dataclass",
                extra={"raw_result": raw_result, "error": str(e)},
            )
            return None


class TvSearchStrategy(SearchStrategy):
    """Strategy for searching TV shows in TMDB."""

    def __init__(self, tv_api: Any, request_executor: Any) -> None:
        """Initialize TV search strategy.

        Args:
            tv_api: TMDB TV API instance
            request_executor: Request executor function
        """
        self._tv_api = tv_api
        self._request_executor = request_executor

    def get_media_type(self) -> Literal["tv"]:
        """Return 'tv' media type."""
        return "tv"

    async def search(self, title: str) -> list[TMDBSearchResult]:
        """Search for TV shows using TMDB API.

        Args:
            title: TV show title to search for

        Returns:
            List of TV show search results
        """
        try:
            # Call TMDB TV search API
            raw_results = await self._request_executor(
                lambda: self._tv_api.search(title)
            )

            if not raw_results or not hasattr(raw_results, "results"):
                logger.debug("No TV results found for '%s'", title)
                return []

            # Convert each result to TMDBSearchResult
            results = []
            for raw_result in raw_results.results:
                try:
                    search_result = self._to_search_result(raw_result)
                    results.append(search_result)
                except (TypeError, KeyError) as e:
                    logger.warning("Failed to convert TV search result: %s", e)
                    continue

            logger.debug("TV search for '%s' returned %d results", title, len(results))
            return results

        except (ConnectionError, TimeoutError) as e:
            context = ErrorContext(
                operation="tv_search",
                additional_data={"title": title},
            )
            if isinstance(e, TimeoutError):
                error = AniVaultNetworkError(
                    ErrorCode.TMDB_API_TIMEOUT,
                    f"TV search timeout for '{title}': {e}",
                    context,
                    original_error=e,
                )
            else:
                _ = AniVaultNetworkError(
                    ErrorCode.TMDB_API_CONNECTION_ERROR,
                    f"TV search connection error for '{title}': {e}",
                    context,
                    original_error=e,
                )
            logger.exception("TV search failed for '%s'", title)
            return []
        except Exception as e:

            context = ErrorContext(
                operation="tv_search",
                additional_data={"title": title, "error_type": type(e).__name__},
            )
            logger.exception("TV search failed for '%s'", title)
            return []


class MovieSearchStrategy(SearchStrategy):
    """Strategy for searching movies in TMDB."""

    def __init__(self, movie_api: Any, request_executor: Any) -> None:
        """Initialize Movie search strategy.

        Args:
            movie_api: TMDB Movie API instance
            request_executor: Request executor function
        """
        self._movie_api = movie_api
        self._request_executor = request_executor

    def get_media_type(self) -> Literal["movie"]:
        """Return 'movie' media type."""
        return "movie"

    async def search(self, title: str) -> list[TMDBSearchResult]:
        """Search for movies using TMDB API.

        Args:
            title: Movie title to search for

        Returns:
            List of movie search results
        """
        try:
            # Call TMDB Movie search API
            raw_results = await self._request_executor(
                lambda: self._movie_api.search(title)
            )

            if not raw_results or not hasattr(raw_results, "results"):
                logger.debug("No movie results found for '%s'", title)
                return []

            # Convert each result to TMDBSearchResult
            results = []
            for raw_result in raw_results.results:
                try:
                    search_result = self._to_search_result(raw_result)
                    results.append(search_result)
                except (TypeError, KeyError) as e:
                    logger.warning("Failed to convert movie search result: %s", e)
                    continue

            logger.debug(
                "Movie search for '%s' returned %d results", title, len(results)
            )
            return results

        except (ConnectionError, TimeoutError) as e:
            context = ErrorContext(
                operation="movie_search",
                additional_data={"title": title},
            )
            if isinstance(e, TimeoutError):
                error = AniVaultNetworkError(
                    ErrorCode.TMDB_API_TIMEOUT,
                    f"Movie search timeout for '{title}': {e}",
                    context,
                    original_error=e,
                )
            else:
                _ = AniVaultNetworkError(
                    ErrorCode.TMDB_API_CONNECTION_ERROR,
                    f"Movie search connection error for '{title}': {e}",
                    context,
                    original_error=e,
                )
            logger.exception("Movie search failed for '%s'", title)
            return []
        except Exception:
            logger.exception("Movie search failed for '%s'", title)
            return []
