"""TMDB API Client wrapper with rate limiting and error handling.

This module provides a wrapper around the tmdbv3api library to abstract away
direct API calls and provide a clean interface for searching for media with
integrated rate limiting, concurrency control, and error handling.
"""

from __future__ import annotations

import asyncio
from typing import Any

from tmdbv3api import TV, Movie, TMDb
from tmdbv3api.exceptions import TMDbException

from anivault.config.settings import get_config

from .rate_limiter import TokenBucketRateLimiter
from .semaphore_manager import SemaphoreManager
from .state_machine import RateLimitState, RateLimitStateMachine


class TMDBClient:
    """TMDB API client with integrated rate limiting and error handling.

    This class provides a high-level interface for interacting with the TMDB API,
    including automatic rate limiting, concurrency control, and intelligent error
    handling with circuit breaker patterns.

    Args:
        rate_limiter: Token bucket rate limiter instance
        semaphore_manager: Semaphore manager for concurrency control
        state_machine: Rate limiting state machine
    """

    def __init__(
        self,
        rate_limiter: TokenBucketRateLimiter | None = None,
        semaphore_manager: SemaphoreManager | None = None,
        state_machine: RateLimitStateMachine | None = None,
    ):
        """Initialize the TMDB client.

        Args:
            rate_limiter: Token bucket rate limiter instance
            semaphore_manager: Semaphore manager for concurrency control
            state_machine: Rate limiting state machine
        """
        self.config = get_config()

        # Initialize components
        self.rate_limiter = rate_limiter or TokenBucketRateLimiter(
            capacity=self.config.tmdb.rate_limit_rps,
            refill_rate=self.config.tmdb.rate_limit_rps,
        )
        self.semaphore_manager = semaphore_manager or SemaphoreManager(
            concurrency_limit=self.config.tmdb.concurrent_requests,
        )
        self.state_machine = state_machine or RateLimitStateMachine()

        # Initialize TMDB API client
        self._tmdb = TMDb()
        self._tmdb.api_key = self.config.tmdb.api_key
        self._tmdb.language = "en"
        self._tmdb.debug = self.config.app.debug

        # Initialize API objects
        self._tv = TV()
        self._movie = Movie()

    async def search_media(self, title: str) -> list[dict[str, Any]]:
        """Search for media (TV shows and movies) by title.

        This method searches both TV shows and movies using the TMDB API
        and returns a combined list of results with metadata.

        Args:
            title: Title to search for

        Returns:
            List of media results with metadata

        Raises:
            TMDbException: If API request fails after all retries
        """
        results = []

        # Search TV shows
        try:
            tv_results = await self._make_request(
                lambda: self._tv.search(title),
                f"TV search for '{title}'",
            )
            for result in tv_results:
                result["media_type"] = "tv"
                results.append(result)
        except TMDbException as e:
            if self.config.app.debug:
                print(f"TV search failed for '{title}': {e}")

        # Search movies
        try:
            movie_results = await self._make_request(
                lambda: self._movie.search(title),
                f"Movie search for '{title}'",
            )
            for result in movie_results:
                result["media_type"] = "movie"
                results.append(result)
        except TMDbException as e:
            if self.config.app.debug:
                print(f"Movie search failed for '{title}': {e}")

        return results

    async def get_media_details(
        self,
        media_id: int,
        media_type: str,
    ) -> dict[str, Any] | None:
        """Get detailed information for a specific media item.

        Args:
            media_id: TMDB ID of the media item
            media_type: Type of media ('tv' or 'movie')

        Returns:
            Detailed media information or None if not found

        Raises:
            TMDbException: If API request fails after all retries
        """
        if media_type == "tv":
            return await self._make_request(
                lambda: self._tv.details(media_id),
                f"TV details for ID {media_id}",
            )
        if media_type == "movie":
            return await self._make_request(
                lambda: self._movie.details(media_id),
                f"Movie details for ID {media_id}",
            )
        error_msg = f"Unsupported media type: {media_type}"
        raise ValueError(error_msg)

    async def _make_request(self, api_call) -> Any:
        """Make a rate-limited and concurrency-controlled API request.

        This method handles all the complexity of rate limiting, concurrency
        control, retry logic, and error handling for TMDB API calls.

        Args:
            api_call: Function that makes the actual API call
            description: Description of the request for logging

        Returns:
            API response data

        Raises:
            TMDbException: If API request fails after all retries
        """
        # Check if we should make the request based on state machine
        if not self.state_machine.should_make_request():
            if self.state_machine.state == RateLimitState.CACHE_ONLY:
                raise TMDbException("Service in cache-only mode due to high error rate")

            # Wait for retry delay
            retry_delay = self.state_machine.get_retry_delay()
            if retry_delay > 0:
                await asyncio.sleep(retry_delay)

        # Use semaphore for concurrency control
        async with self.semaphore_manager:
            # Apply rate limiting
            while not self.rate_limiter.try_acquire():
                await asyncio.sleep(0.1)  # Wait for token availability

            # Make the API call with retry logic
            last_exception = None

            for attempt in range(self.config.tmdb.retry_attempts + 1):
                try:
                    # Make the API call
                    result = api_call()

                    # Handle successful response
                    self.state_machine.handle_success()
                    return result

                except TMDbException as e:
                    last_exception = e

                    # Handle different types of errors
                    if hasattr(e, "response") and e.response is not None:
                        status_code = getattr(e.response, "status_code", 0)

                        if status_code == 429:
                            # Handle rate limiting
                            retry_after = self._extract_retry_after(e.response)
                            self.state_machine.handle_429(retry_after)

                            # Wait for retry delay
                            retry_delay = self.state_machine.get_retry_delay()
                            if retry_delay > 0:
                                await asyncio.sleep(retry_delay)

                            # Reset rate limiter on 429
                            self.rate_limiter.reset()

                        elif 500 <= status_code < 600:
                            # Handle server errors
                            self.state_machine.handle_error(status_code)
                        else:
                            # Handle other client errors
                            self.state_machine.handle_error(status_code)
                    else:
                        # Handle other exceptions
                        self.state_machine.handle_error(0)

                    # Apply exponential backoff for retries
                    if attempt < self.config.tmdb.retry_attempts:
                        backoff_delay = self.config.tmdb.retry_delay * (2**attempt)
                        await asyncio.sleep(backoff_delay)

            # All retries exhausted
            raise last_exception or TMDbException(
                "API request failed after all retries",
            )

    def _extract_retry_after(self, response) -> float | None:
        """Extract Retry-After header value from response.

        Args:
            response: HTTP response object

        Returns:
            Retry-After value in seconds or None if not present
        """
        try:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                return float(retry_after)
        except (ValueError, AttributeError):
            pass

        return None

    def get_stats(self) -> dict[str, Any]:
        """Get current statistics about the client.

        Returns:
            Dictionary containing client statistics
        """
        return {
            "rate_limiter": {
                "tokens_available": self.rate_limiter.get_tokens_available(),
                "capacity": self.rate_limiter.capacity,
                "refill_rate": self.rate_limiter.refill_rate,
            },
            "semaphore_manager": {
                "active_requests": self.semaphore_manager.get_active_count(),
                "available_slots": self.semaphore_manager.get_available_count(),
                "concurrency_limit": self.semaphore_manager.concurrency_limit,
            },
            "state_machine": self.state_machine.get_stats(),
        }

    def reset(self) -> None:
        """Reset all client components to initial state.

        This method resets the rate limiter, semaphore manager, and state machine
        to their initial states, useful for testing or recovery scenarios.
        """
        self.rate_limiter.reset()
        self.state_machine.reset()
        # Note: SemaphoreManager doesn't have a reset method as it's stateless
