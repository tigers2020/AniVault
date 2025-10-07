"""TMDB API Client wrapper with rate limiting and error handling.

This module provides a wrapper around the tmdbv3api library to abstract away
direct API calls and provide a clean interface for searching for media with
integrated rate limiting, concurrency control, and error handling.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from tmdbv3api import TV, Movie, TMDb
from tmdbv3api.exceptions import TMDbException

from anivault.config.settings import get_config
from anivault.shared.constants import MediaType
from anivault.shared.constants.tmdb_messages import (
    TMDBErrorMessages,
    TMDBOperationNames,
)
from anivault.shared.errors import (
    AniVaultError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
)
from anivault.shared.logging import log_operation_error, log_operation_success

from .rate_limiter import TokenBucketRateLimiter
from .semaphore_manager import SemaphoreManager
from .state_machine import RateLimitState, RateLimitStateMachine

logger = logging.getLogger(__name__)


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
        language: str = "ko-KR",
        region: str = "KR",
    ):
        """Initialize the TMDB client.

        Args:
            rate_limiter: Token bucket rate limiter instance
            semaphore_manager: Semaphore manager for concurrency control
            state_machine: Rate limiting state machine
            language: Language code for TMDB API requests (default: ko-KR for Korean)
            region: Region code for TMDB API requests (default: KR)
        """
        self.config = get_config()

        # Initialize components
        self.rate_limiter = rate_limiter or TokenBucketRateLimiter(
            capacity=int(self.config.tmdb.rate_limit_rps),
            refill_rate=int(self.config.tmdb.rate_limit_rps),
        )
        self.semaphore_manager = semaphore_manager or SemaphoreManager(
            concurrency_limit=self.config.tmdb.concurrent_requests,
        )
        self.state_machine = state_machine or RateLimitStateMachine()

        # Initialize TMDB API client - MUST be configured before creating TV/Movie objects
        self._tmdb = TMDb()
        self._tmdb.api_key = self.config.tmdb.api_key
        self._tmdb.language = language  # Set language BEFORE creating TV/Movie objects
        self._tmdb.region = region
        self._tmdb.debug = (
            True  # Force debug to see actual API calls with language parameter
        )

        # Store language for explicit parameter passing
        self.language = language
        self.region = region

        # Initialize API objects AFTER TMDb configuration
        # TV and Movie objects will inherit TMDb configuration
        self._tv = TV()
        self._movie = Movie()

        # Verify configuration is applied
        logger.info(
            "TMDB Client initialized with language: %s, region: %s",
            language,
            region,
        )

    def _generate_shortened_titles(self, title: str) -> list[str]:
        """Generate shortened versions of the title for fallback search.

        Args:
            title: Original title to shorten

        Returns:
            List of shortened titles, ordered by preference (longest first)
        """
        # Split title into words
        words = title.strip().split()
        if len(words) <= 1:
            return []  # Cannot shorten single word titles

        shortened_titles = []

        # Remove common suffixes/versions
        version_patterns = [
            r"\s+v\d+$",  # v1, v2, etc.
            r"\s+version\s+\d+$",  # version 1, version 2, etc.
            r"\s+\d{4}$",  # year at end
            r"\s+\(.*\)$",  # parentheses at end
            r"\s+\[.*\]$",  # brackets at end
            r"\s+ext$",  # ext suffix
            r"\s+special$",  # special suffix
            r"\s+ova$",  # ova suffix
            r"\s+tv$",  # tv suffix
        ]

        import re

        base_title = title
        for pattern in version_patterns:
            base_title = re.sub(pattern, "", base_title, flags=re.IGNORECASE)

        # Add base title without version patterns
        if base_title.strip() != title.strip():
            shortened_titles.append(base_title.strip())

        # Generate progressive word removal (recursive trimming down to 1 word)
        # Example: "이세계 묵시록 마이노그라~파멸의 문명에서 시작하는 세계 정복~"
        #       → "이세계 묵시록 마이노그라~파멸의 문명에서 시작하는"
        #       → "이세계 묵시록 마이노그라~파멸의 문명에서"
        #       → ...
        #       → "이세계 묵시록 마이노그라~"
        #       → "이세계 묵시록"
        #       → "이세계"
        current_words = words.copy()
        while (
            len(current_words) > 1
        ):  # Changed from > 2 to > 1 for more aggressive fallback
            current_words.pop()  # Remove last word
            shortened_titles.append(" ".join(current_words))

        # Remove duplicates while preserving order
        seen = set()
        unique_titles = []
        for title_var in shortened_titles:
            if title_var.lower() not in seen:
                seen.add(title_var.lower())
                unique_titles.append(title_var)

        return unique_titles

    async def search_media(self, title: str) -> list[dict[str, Any]]:
        """Search for media (TV shows and movies) by title.

        This method searches both TV shows and movies using the TMDB API
        and returns a combined list of results with metadata.

        Args:
            title: Title to search for

        Returns:
            List of media results with metadata

        Raises:
            InfrastructureError: If API request fails after all retries
        """
        context = ErrorContext(
            operation="search_media",
            additional_data={"title": title},
        )

        results = []

        # Search TV shows
        try:
            tv_response = await self._make_request(lambda: self._tv.search(title))
            # Extract results from API response (handle both dict and AsObj)
            if hasattr(tv_response, "get"):
                tv_results = tv_response.get("results", [])
            else:
                logger.warning(
                    "TV search returned unexpected response: %s",
                    type(tv_response),
                )
                tv_results = []

            for result in tv_results:
                if isinstance(result, dict):
                    result["media_type"] = MediaType.TV
                    # Use TV show 'name' field as 'title' (name is localized, title is original)
                    if "name" in result:
                        result["title"] = result["name"]  # Always use localized name
                    results.append(result)
                else:
                    # Convert any non-dict object to dict (including AsObj)
                    try:
                        if hasattr(result, "__dict__"):
                            # Convert object with attributes to dict
                            result_dict = {
                                k: v
                                for k, v in result.__dict__.items()
                                if not k.startswith("_")
                            }
                        elif hasattr(result, "get"):
                            # Convert dict-like object to dict
                            result_dict = dict(result)
                        else:
                            # Fallback: create dict from string representation
                            result_dict = {"title": str(result)}

                        result_dict["media_type"] = MediaType.TV
                        # Use TV show 'name' field as 'title' (name is localized, title is original)
                        if "name" in result_dict:
                            result_dict["title"] = result_dict[
                                "name"
                            ]  # Always use localized name
                        results.append(result_dict)
                    except Exception as e:
                        logger.warning(
                            "Failed to convert TV search result %s: %s",
                            type(result),
                            e,
                        )
                        results.append(
                            {"title": str(result), "media_type": MediaType.TV},
                        )
        except AniVaultError as e:
            # Re-raise AniVaultError as-is
            tv_error = e
            log_operation_error(
                logger=logger,
                error=tv_error,
                operation="search_tv_shows",
                additional_context=context.additional_data if context else None,
            )
            # Continue with movie search even if TV search fails
        except Exception as e:  # noqa: BLE001
            # Convert generic exceptions to InfrastructureError
            error = InfrastructureError(
                code=ErrorCode.TMDB_API_REQUEST_FAILED,
                message=f"TV search failed: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                error=error,
                operation="search_tv_shows",
                additional_context=context.additional_data if context else None,
            )
            # Continue with movie search even if TV search fails

        # Search movies
        try:
            movie_response = await self._make_request(lambda: self._movie.search(title))
            # Extract results from API response (handle both dict and AsObj)
            if hasattr(movie_response, "get"):
                movie_results = movie_response.get("results", [])
            else:
                logger.warning(
                    "Movie search returned unexpected response: %s",
                    type(movie_response),
                )
                movie_results = []

            for result in movie_results:
                if isinstance(result, dict):
                    result["media_type"] = MediaType.MOVIE
                    results.append(result)
                else:
                    # Convert any non-dict object to dict (including AsObj)
                    try:
                        if hasattr(result, "__dict__"):
                            # Convert object with attributes to dict
                            result_dict = {
                                k: v
                                for k, v in result.__dict__.items()
                                if not k.startswith("_")
                            }
                        elif hasattr(result, "get"):
                            # Convert dict-like object to dict
                            result_dict = dict(result)
                        else:
                            # Fallback: create dict from string representation
                            result_dict = {"title": str(result)}

                        result_dict["media_type"] = MediaType.MOVIE
                        results.append(result_dict)
                    except Exception as e:
                        logger.warning(
                            "Failed to convert Movie search result %s: %s",
                            type(result),
                            e,
                        )
                        results.append(
                            {"title": str(result), "media_type": MediaType.MOVIE},
                        )
        except AniVaultError as e:
            # Re-raise AniVaultError as-is
            movie_error = e
            log_operation_error(
                logger=logger,
                error=movie_error,
                operation="search_movies",
                additional_context=context.additional_data if context else None,
            )
            # Continue even if movie search fails
        except Exception as e:  # noqa: BLE001
            # Convert generic exceptions to InfrastructureError
            error = InfrastructureError(
                code=ErrorCode.TMDB_API_REQUEST_FAILED,
                message=f"Movie search failed: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                error=error,
                operation="search_movies",
                additional_context=context.additional_data if context else None,
            )
            # Continue even if movie search fails

        # If both searches failed, try with shortened title
        if not results:
            shortened_titles = self._generate_shortened_titles(title)
            for shortened_title in shortened_titles:
                logger.debug("Trying shortened title: %s", shortened_title)
                try:
                    # Try TV search with shortened title
                    try:
                        tv_response = await self._make_request(
                            lambda: self._tv.search(shortened_title),
                        )
                        if hasattr(tv_response, "get"):
                            tv_results = tv_response.get("results", [])
                        else:
                            tv_results = []

                        for result in tv_results:
                            if isinstance(result, dict):
                                result["media_type"] = MediaType.TV
                                # Use TV show 'name' field as 'title' (name is localized, title is original)
                                if "name" in result:
                                    result["title"] = result[
                                        "name"
                                    ]  # Always use localized name
                                results.append(result)
                            else:
                                try:
                                    if hasattr(result, "__dict__"):
                                        result_dict = {
                                            k: v
                                            for k, v in result.__dict__.items()
                                            if not k.startswith("_")
                                        }
                                    elif hasattr(result, "get"):
                                        result_dict = dict(result)
                                    else:
                                        result_dict = {"title": str(result)}

                                    result_dict["media_type"] = MediaType.TV
                                    # Use TV show 'name' field as 'title' (name is localized, title is original)
                                    if "name" in result_dict:
                                        result_dict["title"] = result_dict[
                                            "name"
                                        ]  # Always use localized name
                                    results.append(result_dict)
                                except Exception:
                                    results.append(
                                        {
                                            "title": str(result),
                                            "media_type": MediaType.TV,
                                        },
                                    )
                    except Exception as e:
                        # TV search failed, continue with movie search (graceful)
                        logger.debug(
                            "TV search failed, continuing with movie search: %s",
                            str(e),
                            extra={"title": title, "error_type": type(e).__name__},
                        )

                    # Try movie search with shortened title
                    try:
                        movie_response = await self._make_request(
                            lambda: self._movie.search(shortened_title),
                        )
                        if hasattr(movie_response, "get"):
                            movie_results = movie_response.get("results", [])
                        else:
                            movie_results = []

                        for result in movie_results:
                            if isinstance(result, dict):
                                result["media_type"] = MediaType.MOVIE
                                results.append(result)
                            else:
                                try:
                                    if hasattr(result, "__dict__"):
                                        result_dict = {
                                            k: v
                                            for k, v in result.__dict__.items()
                                            if not k.startswith("_")
                                        }
                                    elif hasattr(result, "get"):
                                        result_dict = dict(result)
                                    else:
                                        result_dict = {"title": str(result)}

                                    result_dict["media_type"] = MediaType.MOVIE
                                    results.append(result_dict)
                                except Exception:
                                    results.append(
                                        {
                                            "title": str(result),
                                            "media_type": MediaType.MOVIE,
                                        },
                                    )
                    except Exception as e:
                        # Movie search with this shortened title failed, try next (graceful)
                        logger.debug(
                            "Movie search failed for shortened title '%s', trying next: %s",
                            shortened_title,
                            str(e),
                            extra={
                                "original_title": title,
                                "error_type": type(e).__name__,
                            },
                        )

                    # If we found results with shortened title, break
                    if results:
                        logger.info(
                            "Found results with shortened title '%s' for original '%s'",
                            shortened_title,
                            title,
                        )
                        break

                except Exception as e:
                    logger.debug(
                        "Shortened title '%s' also failed: %s",
                        shortened_title,
                        e,
                    )
                    continue

            # If still no results after trying all shortened titles, raise error
            if not results:
                error = InfrastructureError(
                    code=ErrorCode.TMDB_API_MEDIA_NOT_FOUND,
                    message=f"No media found for title: {title} (tried shortened versions: {shortened_titles})",
                    context=context,
                )
                log_operation_error(
                    logger=logger,
                    error=error,
                    operation="search_media",
                    additional_context=context.additional_data if context else None,
                )
                raise error

        log_operation_success(
            logger=logger,
            operation="search_media",
            duration_ms=0,  # Duration would be calculated in _make_request
            context=context.additional_data if context else None,
        )
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
            InfrastructureError: If API request fails after all retries
        """
        context = ErrorContext(
            operation="get_media_details",
            additional_data={"media_id": media_id, "media_type": media_type},
        )

        if media_type not in ["tv", "movie"]:
            error = InfrastructureError(
                code=ErrorCode.TMDB_API_INVALID_MEDIA_TYPE,
                message=f"Unsupported media type: {media_type}",
                context=context,
            )
            log_operation_error(
                logger=logger,
                error=error,
                operation="get_media_details",
                additional_context=context.additional_data if context else None,
            )
            raise error

        try:
            if media_type == MediaType.TV:
                result = await self._make_request(lambda: self._tv.details(media_id))
            else:  # movie
                result = await self._make_request(lambda: self._movie.details(media_id))

            # Use TV show 'name' field as 'title' (name is localized, title is original)
            if isinstance(result, dict) and media_type == MediaType.TV:
                if "name" in result:
                    result["title"] = result["name"]  # Always use localized name

            log_operation_success(
                logger=logger,
                operation="get_media_details",
                duration_ms=0,  # Duration would be calculated in _make_request
                context=context.additional_data if context else None,
            )
            return result if isinstance(result, dict) else None

        except AniVaultError as e:
            # Re-raise AniVaultError as-is
            details_error = e
            log_operation_error(
                logger=logger,
                error=details_error,
                operation="get_media_details",
                additional_context=context.additional_data if context else None,
            )
            raise
        except Exception as e:
            # Convert generic exceptions to InfrastructureError
            error = InfrastructureError(
                code=ErrorCode.TMDB_API_REQUEST_FAILED,
                message=f"Media details request failed: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                error=error,
                operation="get_media_details",
                additional_context=context.additional_data if context else None,
            )
            raise error from e

    async def _make_request(self, api_call: Callable[[], Any]) -> Any:
        """Make a rate-limited and concurrency-controlled API request.

        This method orchestrates the API request process by coordinating
        state machine checks, concurrency control, rate limiting, and retry logic.

        Args:
            api_call: Function that makes the actual API call

        Returns:
            API response data

        Raises:
            InfrastructureError: If API request fails after all retries
        """
        context = ErrorContext(
            operation="make_tmdb_request",
            additional_data={"retry_attempts": self.config.tmdb.retry_attempts},
        )

        # Check if we should make the request based on state machine
        await self._check_request_permissibility(context)

        # Use semaphore for concurrency control
        async with self.semaphore_manager:
            # Apply rate limiting
            await self._apply_rate_limiting()

            # Make the API call with retry logic
            return await self._execute_with_retry(api_call, context)

    async def _check_request_permissibility(self, context: ErrorContext) -> None:
        """Check if the request should be made based on state machine.

        Args:
            context: Error context for logging

        Raises:
            InfrastructureError: If service is in cache-only mode
        """
        if not self.state_machine.should_make_request():
            if self.state_machine.state == RateLimitState.CACHE_ONLY:
                error = InfrastructureError(
                    code=ErrorCode.TMDB_API_RATE_LIMIT_EXCEEDED,
                    message="Service in cache-only mode due to high error rate",
                    context=context,
                )
                log_operation_error(
                    logger=logger,
                    error=error,
                    operation="make_tmdb_request",
                    additional_context=context.additional_data if context else None,
                )
                raise error

            # Wait for retry delay
            retry_delay = self.state_machine.get_retry_delay()
            if retry_delay > 0:
                await asyncio.sleep(retry_delay)

    async def _apply_rate_limiting(self) -> None:
        """Apply rate limiting by waiting for token availability.

        This method blocks until a token is available from the rate limiter.
        """
        while not self.rate_limiter.try_acquire():
            await asyncio.sleep(0.1)  # Wait for token availability

    async def _execute_with_retry(
        self,
        api_call: Callable[[], Any],
        context: ErrorContext,
    ) -> Any:
        """Execute API call with retry logic and error handling.

        Args:
            api_call: Function that makes the actual API call
            context: Error context for logging

        Returns:
            API response data

        Raises:
            InfrastructureError: If API request fails after all retries
        """
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
                await self._handle_tmdb_exception(e, attempt, context)

        # All retries exhausted
        return await self._handle_retry_exhaustion(last_exception, context)

    async def _handle_tmdb_exception(
        self,
        exception: TMDbException,
        attempt: int,
        context: ErrorContext,
    ) -> None:
        """Handle TMDbException with appropriate error processing and retry logic.

        Args:
            exception: The TMDbException to handle
            attempt: Current attempt number
            context: Error context for logging
        """
        # Convert TMDbException to InfrastructureError
        error_code, error_message = self._convert_tmdb_exception(exception)

        InfrastructureError(
            code=error_code,
            message=error_message,
            context=context,
            original_error=exception,
        )

        # Handle different types of errors
        await self._process_error_response(exception, context)

        # Apply exponential backoff for retries
        if attempt < self.config.tmdb.retry_attempts:
            backoff_delay = self.config.tmdb.retry_delay * (2**attempt)
            await asyncio.sleep(backoff_delay)

    async def _process_error_response(
        self,
        exception: TMDbException,
        context: ErrorContext,  # noqa: ARG002
    ) -> None:
        """Process error response and update state machine accordingly.

        Args:
            exception: The TMDbException to process
            context: Error context for logging
        """
        if hasattr(exception, "response") and exception.response is not None:
            status_code = getattr(exception.response, "status_code", 0)

            if status_code == 429:
                # Handle rate limiting
                retry_after = self._extract_retry_after(exception.response)
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

    async def _handle_retry_exhaustion(
        self,
        last_exception: TMDbException | None,
        context: ErrorContext,
    ) -> Any:
        """Handle the case when all retries have been exhausted.

        Args:
            last_exception: The last exception that occurred
            context: Error context for logging

        Returns:
            API response data (never reached due to exception)

        Raises:
            InfrastructureError: Always raises an error
        """
        if last_exception:
            error_code, error_message = self._convert_tmdb_exception(last_exception)
            final_error = InfrastructureError(
                code=error_code,
                message=f"{error_message} (after {self.config.tmdb.retry_attempts} retries)",
                context=context,
                original_error=last_exception,
            )
            log_operation_error(
                logger=logger,
                error=final_error,
                operation="make_tmdb_request",
                additional_context=context.additional_data if context else None,
            )
            raise final_error
        error = InfrastructureError(
            code=ErrorCode.TMDB_API_REQUEST_FAILED,
            message="API request failed after all retries",
            context=context,
        )
        log_operation_error(
            logger=logger,
            error=error,
            operation="make_tmdb_request",
            additional_context=context.additional_data if context else None,
        )
        raise error

    def _convert_tmdb_exception(  # noqa: PLR0911
        self,
        exception: TMDbException,
    ) -> tuple[ErrorCode, str]:
        """Convert TMDbException to appropriate ErrorCode and message.

        Args:
            exception: The TMDbException to convert

        Returns:
            Tuple of (ErrorCode, error_message)
        """
        if hasattr(exception, "response") and exception.response is not None:
            status_code = getattr(exception.response, "status_code", 0)

            if status_code == 401:
                return (
                    ErrorCode.TMDB_API_AUTHENTICATION_ERROR,
                    TMDBErrorMessages.AUTHENTICATION_FAILED,
                )
            if status_code == 403:
                return (
                    ErrorCode.TMDB_API_AUTHENTICATION_ERROR,
                    TMDBErrorMessages.ACCESS_FORBIDDEN,
                )
            if status_code == 429:
                return (
                    ErrorCode.TMDB_API_RATE_LIMIT_EXCEEDED,
                    TMDBErrorMessages.RATE_LIMIT_EXCEEDED,
                )
            if 400 <= status_code < 500:
                return (
                    ErrorCode.TMDB_API_REQUEST_FAILED,
                    TMDBErrorMessages.CLIENT_ERROR.format(status_code=status_code),
                )
            if 500 <= status_code < 600:
                return (
                    ErrorCode.TMDB_API_SERVER_ERROR,
                    TMDBErrorMessages.SERVER_ERROR.format(status_code=status_code),
                )
            return (
                ErrorCode.TMDB_API_REQUEST_FAILED,
                TMDBErrorMessages.REQUEST_FAILED.format(status_code=status_code),
            )
        # No response object, check exception message
        message = str(exception).lower()
        if "timeout" in message:
            return ErrorCode.TMDB_API_TIMEOUT, TMDBErrorMessages.TIMEOUT
        if "connection" in message:
            return (
                ErrorCode.TMDB_API_CONNECTION_ERROR,
                TMDBErrorMessages.CONNECTION_FAILED,
            )
        return (
            ErrorCode.TMDB_API_REQUEST_FAILED,
            TMDBErrorMessages.REQUEST_FAILED.format(status_code=str(exception)),
        )

    def _extract_retry_after(self, response: Any) -> float | None:
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
        except (ValueError, AttributeError) as e:
            # Invalid Retry-After value, return None (caller handles default)
            logger.debug(
                "Failed to parse Retry-After header: %s",
                str(e),
                extra={
                    "header_value": response.headers.get("Retry-After"),
                    "error_type": type(e).__name__,
                },
            )

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
