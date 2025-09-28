"""Enhanced TMDB service with robust rate limiting and caching."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from requests_cache import CachedSession
from tmdbv3api import TV, Movie, Search, TMDb
from tmdbv3api.exceptions import TMDbException
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)


class RobustTMDb(TMDb):
    """
    A subclass of tmdbv3api.TMDb that adds robust handling for
    HTTP 429 rate-limiting errors by respecting the Retry-After header.
    """

    def __init__(self, max_retries: int = 5, proactive_delay_ms: int = 50):
        """Initialize the robust TMDB client.

        Args:
            max_retries: Maximum number of retries for failed requests
            proactive_delay_ms: Proactive delay in milliseconds to avoid rate limits
        """
        super().__init__()
        self._max_retries = max_retries
        self._proactive_delay_ms = proactive_delay_ms

    def _call(self, url: str, params: dict) -> dict:
        """
        Overrides the base _call method to add retry logic for 429 errors.

        Args:
            url: The API endpoint URL
            params: Request parameters

        Returns:
            JSON response from the API

        Raises:
            TMDbException: If all retries are exhausted
        """
        # Proactive delay to avoid hitting rate limits in the first place
        if self._proactive_delay_ms > 0:
            time.sleep(self._proactive_delay_ms / 1000)

        for attempt in range(self._max_retries):
            try:
                # Make the request using the session
                response = self._session.get(url, params=params)

                # Check for HTTP 429 Too Many Requests
                http_too_many_requests = 429
                if response.status_code == http_too_many_requests:
                    retry_after = response.headers.get("Retry-After")
                    wait_time = self._parse_retry_after(retry_after)

                    log.warning(
                        "Rate limit exceeded. Waiting for %.2f seconds. "
                        "Attempt %d/%d.",
                        wait_time,
                        attempt + 1,
                        self._max_retries,
                    )
                    time.sleep(wait_time)
                    continue  # Retry the request

                # Raise an exception for other client/server errors
                response.raise_for_status()

                # If successful, return the JSON payload
                return response.json()

            except requests.exceptions.RequestException as e:
                # This catches connection errors, timeouts, etc.
                log.exception(
                    "Network error during API call. Attempt %d/%d.",
                    attempt + 1,
                    self._max_retries,
                )
                if attempt + 1 == self._max_retries:
                    error_msg = (
                        f"Failed to call TMDB API after {self._max_retries} retries"
                    )
                    raise TMDbException(error_msg) from e
                time.sleep(2**attempt)  # Exponential backoff for network errors

        error_msg = f"Failed to call TMDB API after {self._max_retries} retries."
        raise TMDbException(error_msg)

    def _parse_retry_after(self, retry_after: str | None) -> float:
        """
        Parses the Retry-After header, which can be an integer (seconds)
        or an HTTP-date. Defaults to a safe value if header is missing.

        Args:
            retry_after: The Retry-After header value

        Returns:
            Number of seconds to wait
        """
        if not retry_after:
            return 5.0  # Default wait time if header is absent

        # If it's a number, it's seconds
        if retry_after.isdigit():
            return float(retry_after)

        # If it's a date, calculate the delta from now
        try:
            retry_date = datetime.strptime(retry_after, "%a, %d %b %Y %H:%M:%S GMT")
            retry_date = retry_date.replace(tzinfo=timezone.utc)
            delta = (retry_date - datetime.now(timezone.utc)).total_seconds()
            return max(0, delta)  # Ensure we don't wait a negative duration
        except ValueError:
            log.warning(
                "Could not parse Retry-After date: %s. Defaulting to 5s.",
                retry_after,
            )
            return 5.0


class TMDBService:
    """
    A high-level service for interacting with the TMDB API,
    incorporating robust session management, rate-limiting, and caching.
    """

    def __init__(
        self,
        api_key: str,
        cache_name: str = "tmdb_cache",
        cache_expire_after: int = 86400,
    ):
        """Initialize the TMDB service.

        Args:
            api_key: TMDB API key
            cache_name: Name for the cache database
            cache_expire_after: Cache expiration time in seconds (default: 1 day)
        """
        if not api_key:
            error_msg = "TMDB API key is required."
            raise ValueError(error_msg)

        # Create a robust session with caching
        self.session = self._create_cached_session(cache_name, cache_expire_after)

        # Initialize our robust client with the session
        self.tmdb = RobustTMDb()
        self.tmdb.api_key = api_key
        self.tmdb.language = "en"
        self.tmdb.session = self.session  # CRITICAL: Pass the session to the client

        # Initialize API objects
        self.movie_search = Search()
        self.tv_search = Search()
        self.movie = Movie()
        self.tv = TV()

        log.info("TMDB service initialized with API key ending in ...%s", api_key[-4:])

    def _create_cached_session(
        self,
        cache_name: str,
        cache_expire_after: int,
    ) -> CachedSession:
        """Create a cached session with robust retry strategy.

        Args:
            cache_name: Name for the cache database
            cache_expire_after: Cache expiration time in seconds

        Returns:
            Configured CachedSession
        """
        # Create cached session
        session = CachedSession(
            cache_name=cache_name,
            backend="sqlite",
            expire_after=cache_expire_after,
            cache_control=True,
            stale_if_error=True,
        )

        # Configure retry strategy for non-429 errors
        retry_strategy = Retry(
            total=3,
            status_forcelist=[500, 502, 503, 504],
            backoff_factor=1,  # E.g., sleep for 1s, 2s, 4s between retries
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)

        # Set common headers
        session.headers["User-Agent"] = "AniVault/1.0 (anime-file-organizer)"

        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def search_movie(self, title: str) -> dict[str, Any] | None:
        """Search for a movie and return the top result.

        Args:
            title: Movie title to search for

        Returns:
            Movie data dict or None if not found
        """
        try:
            results = self.movie_search.movies({"query": title})
            if results:
                log.debug("Found %d movie results for '%s'", len(results), title)
                return results[0]  # Return the raw dict
        except TMDbException:
            log.exception("TMDB API error while searching for movie '%s'", title)
        return None

    def search_tv(self, title: str) -> dict[str, Any] | None:
        """Search for a TV show and return the top result.

        Args:
            title: TV show title to search for

        Returns:
            TV show data dict or None if not found
        """
        try:
            results = self.tv_search.tv_shows({"query": title})
            if results:
                log.debug("Found %d TV results for '%s'", len(results), title)
                return results[0]  # Return the raw dict
        except TMDbException:
            log.exception("TMDB API error while searching for TV show '%s'", title)
        return None

    def get_movie_details(self, movie_id: int) -> dict[str, Any] | None:
        """Get detailed information for a movie.

        Args:
            movie_id: TMDB movie ID

        Returns:
            Movie details dict or None if not found
        """
        try:
            details = self.movie.details(movie_id)
            log.debug("Retrieved movie details for ID %d", movie_id)
            return details
        except TMDbException:
            log.exception(
                "TMDB API error while getting movie details for ID %d",
                movie_id,
            )
        return None

    def get_tv_details(self, tv_id: int) -> dict[str, Any] | None:
        """Get detailed information for a TV show.

        Args:
            tv_id: TMDB TV show ID

        Returns:
            TV show details dict or None if not found
        """
        try:
            details = self.tv.details(tv_id)
            log.debug("Retrieved TV details for ID %d", tv_id)
            return details
        except TMDbException:
            log.exception("TMDB API error while getting TV details for ID %d", tv_id)
        return None

    def get_tv_season_details(
        self,
        tv_id: int,
        season_number: int,
    ) -> dict[str, Any] | None:
        """Get details for a specific TV season.

        Args:
            tv_id: TMDB TV show ID
            season_number: Season number

        Returns:
            Season details dict or None if not found
        """
        try:
            season_details = self.tv.season(tv_id, season_number)
            log.debug("Retrieved season %d details for TV ID %d", season_number, tv_id)
            return season_details
        except TMDbException:
            log.exception(
                "TMDB API error while getting season %d for TV ID %d",
                season_number,
                tv_id,
            )
        return None

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Cache statistics dictionary
        """
        if hasattr(self.session, "cache"):
            return {
                "cache_name": self.session.cache.cache_name,
                "hit_count": getattr(self.session.cache, "hit_count", 0),
                "miss_count": getattr(self.session.cache, "miss_count", 0),
                "total_requests": getattr(self.session.cache, "total_requests", 0),
            }
        return {"cache_stats": "Not available"}

    def clear_cache(self) -> None:
        """Clear the cache."""
        if hasattr(self.session, "cache"):
            self.session.cache.clear()
            log.info("TMDB cache cleared")

    def close(self) -> None:
        """Close the service and cleanup resources."""
        if hasattr(self.session, "close"):
            self.session.close()
        log.info("TMDB service closed")
