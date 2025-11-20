"""TMDB Search Strategy Pattern Implementation.

This module implements the Strategy pattern for TMDB media search operations,
eliminating code duplication between TV and Movie search logic.

The Strategy pattern allows the TMDBClient to delegate media-type-specific
search operations to concrete strategy implementations while maintaining
a consistent interface.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Literal

from pydantic import ValidationError

from anivault.services.tmdb_models import TMDBMediaDetails, TMDBSearchResult

logger = logging.getLogger(__name__)


class SearchStrategy(ABC):
    """Abstract base class for TMDB search strategies.

    This class defines the interface for TV and Movie search strategies,
    ensuring consistent behavior across different media types while allowing
    type-specific implementations.

    Concrete implementations (TvSearchStrategy, MovieSearchStrategy) must
    implement the search() method to perform media-type-specific API calls
    and result normalization.

    Example:
        >>> tv_strategy = TvSearchStrategy(tv_api, rate_limiter)
        >>> results = await tv_strategy.search("Attack on Titan")
        >>> assert all(isinstance(r, TMDBSearchResult) for r in results)
    """

    @abstractmethod
    async def search(self, title: str) -> list[TMDBSearchResult]:
        """Search for media by title.

        Performs a media-type-specific search (TV or Movie) using the TMDB API
        and returns validated Pydantic models.

        Args:
            title: Media title to search for

        Returns:
            List of TMDBSearchResult models (validated by Pydantic)
            Returns empty list if search fails or no results found

        Raises:
            InfrastructureError: If API request fails after retries
            ValidationError: If API response doesn't match expected schema
        """
        ...

    @abstractmethod
    async def get_details(self, media_id: int) -> TMDBMediaDetails | None:
        """Get detailed information for a specific media item.

        Args:
            media_id: TMDB ID of the media item

        Returns:
            TMDBMediaDetails model or None if not found/validation fails

        Raises:
            InfrastructureError: If API request fails after retries
        """
        ...

    @abstractmethod
    def get_media_type(self) -> Literal["tv", "movie"]:
        """Get the media type handled by this strategy.

        Returns:
            Media type identifier ("tv" or "movie")
        """
        ...

    def _to_search_result(self, raw_result: Any) -> TMDBSearchResult:
        """Convert raw API result to TMDBSearchResult model.

        Directly validates raw API response using Pydantic model_validate,
        which handles dict, dict-like objects, and objects with __dict__.

        Args:
            raw_result: Raw result from TMDB API (dict or dict-like object)

        Returns:
            Validated TMDBSearchResult model

        Raises:
            ValidationError: If result data doesn't match TMDBSearchResult schema

        Note:
            BaseTypeModel (via extra="ignore") gracefully handles unknown fields
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

        # Direct Pydantic validation (extra='ignore' handles unknown fields)
        return TMDBSearchResult.model_validate(data)

    def _to_details_model(self, raw_result: Any) -> TMDBMediaDetails | None:
        """Convert raw API details result to TMDBMediaDetails model.

        Directly validates raw API response using Pydantic model_validate.

        Args:
            raw_result: Raw details result from TMDB API

        Returns:
            Validated TMDBMediaDetails model or None if validation fails
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

            # Direct Pydantic validation
            return TMDBMediaDetails.model_validate(data)

        except ValidationError:
            logger.exception(
                "Failed to parse media details into Pydantic model",
                extra={"raw_result": raw_result},
            )
            return None


class TvSearchStrategy(SearchStrategy):
    """TV show search strategy implementation.

    This strategy handles TV-specific search operations including API calls,
    result extraction, and normalization to TMDBSearchResult models.

    Args:
        tv_api: TMDB TV API instance (tmdbv3api.TV)
        request_executor: Async function to execute API requests with rate limiting

    Example:
        >>> from tmdbv3api import TV
        >>> tv_strategy = TvSearchStrategy(TV(), client._make_request)
        >>> results = await tv_strategy.search("Attack on Titan")
        >>> assert all(r.media_type == "tv" for r in results)
    """

    def __init__(
        self,
        tv_api: Any,  # tmdbv3api.TV
        request_executor: Callable[[Callable[[], Any]], Any],
    ):
        """Initialize TV search strategy.

        Args:
            tv_api: TMDB TV API instance
            request_executor: Async function to execute API requests
        """
        self._tv = tv_api
        self._request_executor = request_executor

    async def search(self, title: str) -> list[TMDBSearchResult]:
        """Search for TV shows by title.

        Args:
            title: TV show title to search for

        Returns:
            List of TMDBSearchResult models with media_type="tv"
            Returns empty list if search fails or no results found
        """
        try:
            # Execute API request with rate limiting
            raw_response = await self._request_executor(lambda: self._tv.search(title))

            # Extract results from response
            if hasattr(raw_response, "get"):
                raw_results = raw_response.get("results", [])
            else:
                logger.warning(
                    "TV search returned unexpected response type: %s",
                    type(raw_response),
                )
                return []

            # Convert to Pydantic models
            results = []
            for raw_result in raw_results:
                try:
                    result_model = self._to_search_result(raw_result)
                    results.append(result_model)
                except ValidationError as e:
                    logger.warning(
                        "Failed to parse TV search result: %s",
                        e,
                        extra={"raw_result": raw_result},
                    )
                    continue
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "Unexpected error processing TV result (%s): %s",
                        type(raw_result),
                        e,
                    )
                    continue

            return results

        except Exception:
            logger.exception("TV search failed for '%s'", title)
            return []

    async def get_details(self, media_id: int) -> TMDBMediaDetails | None:
        """Get detailed TV show information.

        Args:
            media_id: TMDB TV show ID

        Returns:
            TMDBMediaDetails model or None if validation fails
        """
        try:
            raw_result = await self._request_executor(
                lambda: self._tv.details(media_id),
            )
            return self._to_details_model(raw_result)

        except Exception:
            logger.exception("Failed to get TV details for ID %s", media_id)
            return None

    def get_media_type(self) -> Literal["tv", "movie"]:
        """Get media type handled by this strategy.

        Returns:
            "tv" media type identifier
        """
        return "tv"


class MovieSearchStrategy(SearchStrategy):
    """Movie search strategy implementation.

    This strategy handles movie-specific search operations including API calls,
    result extraction, and normalization to TMDBSearchResult models.

    Args:
        movie_api: TMDB Movie API instance (tmdbv3api.Movie)
        request_executor: Async function to execute API requests with rate limiting

    Example:
        >>> from tmdbv3api import Movie
        >>> movie_strategy = MovieSearchStrategy(Movie(), client._make_request)
        >>> results = await movie_strategy.search("Your Name")
        >>> assert all(r.media_type == "movie" for r in results)
    """

    def __init__(
        self,
        movie_api: Any,  # tmdbv3api.Movie
        request_executor: Callable[[Callable[[], Any]], Any],
    ):
        """Initialize movie search strategy.

        Args:
            movie_api: TMDB Movie API instance
            request_executor: Async function to execute API requests
        """
        self._movie = movie_api
        self._request_executor = request_executor

    async def search(self, title: str) -> list[TMDBSearchResult]:
        """Search for movies by title.

        Args:
            title: Movie title to search for

        Returns:
            List of TMDBSearchResult models with media_type="movie"
            Returns empty list if search fails or no results found
        """
        try:
            # Execute API request with rate limiting
            raw_response = await self._request_executor(
                lambda: self._movie.search(title),
            )

            # Extract results from response
            if hasattr(raw_response, "get"):
                raw_results = raw_response.get("results", [])
            else:
                logger.warning(
                    "Movie search returned unexpected response type: %s",
                    type(raw_response),
                )
                return []

            # Convert to Pydantic models
            results = []
            for raw_result in raw_results:
                try:
                    result_model = self._to_search_result(raw_result)
                    results.append(result_model)
                except ValidationError as e:
                    logger.warning(
                        "Failed to parse Movie search result: %s",
                        e,
                        extra={"raw_result": raw_result},
                    )
                    continue
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "Unexpected error processing Movie result (%s): %s",
                        type(raw_result),
                        e,
                    )
                    continue

            return results

        except Exception:
            logger.exception("Movie search failed for '%s'", title)
            return []

    async def get_details(self, media_id: int) -> TMDBMediaDetails | None:
        """Get detailed movie information.

        Args:
            media_id: TMDB movie ID

        Returns:
            TMDBMediaDetails model or None if validation fails
        """
        try:
            raw_result = await self._request_executor(
                lambda: self._movie.details(media_id),
            )
            return self._to_details_model(raw_result)

        except Exception:
            logger.exception("Failed to get Movie details for ID %s", media_id)
            return None

    def get_media_type(self) -> Literal["tv", "movie"]:
        """Get media type handled by this strategy.

        Returns:
            "movie" media type identifier
        """
        return "movie"
