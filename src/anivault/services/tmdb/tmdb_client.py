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
from anivault.services.rate_limiter import TokenBucketRateLimiter
from anivault.services.semaphore_manager import SemaphoreManager
from anivault.services.state_machine import RateLimitState, RateLimitStateMachine
from anivault.shared.constants import HTTPStatusCodes, LogContextKeys, MediaType
from anivault.shared.constants.tmdb_messages import TMDBErrorMessages
from anivault.shared.errors import (
    AniVaultError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
)
from anivault.shared.logging import log_operation_error, log_operation_success

from .tmdb_models import TMDBMediaDetails, TMDBSearchResponse, TMDBSearchResult
from .tmdb_strategies import MovieSearchStrategy, SearchStrategy, TvSearchStrategy
from .tmdb_utils import generate_shortened_titles

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
        # Migrated to new Settings structure (Task 12: API compatibility)
        # Old: self.config.tmdb → New: self.config.api.tmdb
        self.rate_limiter = rate_limiter or TokenBucketRateLimiter(
            capacity=int(self.config.api.tmdb.rate_limit_rps),
            refill_rate=int(self.config.api.tmdb.rate_limit_rps),
        )
        self.semaphore_manager = semaphore_manager or SemaphoreManager(
            concurrency_limit=self.config.api.tmdb.concurrent_requests,
        )
        self.state_machine = state_machine or RateLimitStateMachine()

        # Initialize TMDB API client - MUST be configured before creating TV/Movie objects
        self._tmdb = TMDb()
        self._tmdb.api_key = self.config.api.tmdb.api_key
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

        # Initialize search strategies
        self._tv_strategy = TvSearchStrategy(
            tv_api=self._tv,
            request_executor=self._make_request,
        )
        self._movie_strategy = MovieSearchStrategy(
            movie_api=self._movie,
            request_executor=self._make_request,
        )

        # Verify configuration is applied
        logger.info(
            "TMDB Client initialized with language: %s, region: %s",
            language,
            region,
        )

    def _get_strategies(self) -> list[SearchStrategy]:
        """Get all search strategies to try.

        Returns:
            List of search strategies (TV and Movie)
        """
        return [self._tv_strategy, self._movie_strategy]

    async def _search_with_strategies(
        self,
        title: str,
        strategies: list[SearchStrategy] | None = None,
    ) -> list[TMDBSearchResult]:
        """Execute search using all strategies and combine results.

        Args:
            title: Title to search for
            strategies: List of strategies to use (defaults to all strategies)

        Returns:
            Combined list of search results from all strategies
        """
        if strategies is None:
            strategies = self._get_strategies()

        all_results: list[TMDBSearchResult] = []

        for strategy in strategies:
            try:
                results = await strategy.search(title)
                all_results.extend(results)
            except Exception as e:  # noqa: BLE001
                # Strategies already log their own errors
                # Just continue with next strategy
                logger.debug(
                    "Strategy %s failed for '%s': %s",
                    strategy.__class__.__name__,
                    title,
                    e,
                )
                continue

        return all_results

    async def search_media(self, title: str) -> TMDBSearchResponse:
        """Search for media (TV shows and movies) by title.

        Uses Strategy pattern to search both TV and Movie with automatic
        fallback to shortened titles if no results found.

        This method implements the Template Method pattern:
        1. Try primary search with all strategies
        2. If no results, try shortened title variations
        3. Return combined results or raise error

        Args:
            title: Title to search for

        Returns:
            TMDBSearchResponse with typed search results

        Raises:
            InfrastructureError: If API request fails or no media found
        """
        context = ErrorContext(
            operation="search_media",
            additional_data={"title": title},
        )

        # 1. Try primary search with all strategies
        results = await self._search_with_strategies(title)

        # 2. Fallback to shortened titles if no results
        if not results:
            shortened_titles = generate_shortened_titles(title)
            for shortened_title in shortened_titles:
                logger.debug("Trying shortened title: %s", shortened_title)
                results = await self._search_with_strategies(shortened_title)
                if results:
                    logger.info(
                        "Found results with shortened title '%s' for original '%s'",
                        shortened_title,
                        title,
                    )
                    break

        # 3. If still no results, raise error
        if not results:
            error = InfrastructureError(
                code=ErrorCode.TMDB_API_MEDIA_NOT_FOUND,
                message=f"No media found for title: {title}",
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
            duration_ms=0,  # Duration calculated in _make_request
            context=context.additional_data if context else None,
        )

        # Return combined results wrapped in response model
        return TMDBSearchResponse(
            page=1,
            total_pages=1,
            total_results=len(results),
            results=results,
        )

    async def get_media_details(
        self,
        media_id: int,
        media_type: str,
    ) -> TMDBMediaDetails | None:
        """Get detailed information for a specific media item.

        Uses Strategy pattern to delegate to media-type-specific implementation.

        Args:
            media_id: TMDB ID of the media item
            media_type: Type of media ('tv' or 'movie')

        Returns:
            TMDBMediaDetails or None if not found

        Raises:
            InfrastructureError: If media_type is invalid or API request fails
        """
        context = ErrorContext(
            operation="get_media_details",
            additional_data={"media_id": media_id, "media_type": media_type},
        )

        # Validate media_type
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

        # Select strategy based on media_type
        strategy = (
            self._tv_strategy if media_type == MediaType.TV else self._movie_strategy
        )

        try:
            # Delegate to strategy
            details = await strategy.get_details(media_id)

            if details:
                log_operation_success(
                    logger=logger,
                    operation="get_media_details",
                    duration_ms=0,
                    context=context.additional_data if context else None,
                )

            return details

        except AniVaultError:
            # Strategy already logged the error
            raise
        except Exception as e:
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
            additional_data={"retry_attempts": self.config.api.tmdb.retry_attempts},
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

        for attempt in range(self.config.api.tmdb.retry_attempts + 1):
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
        if attempt < self.config.api.tmdb.retry_attempts:
            backoff_delay = self.config.api.tmdb.retry_delay * (2**attempt)
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
            status_code = getattr(exception.response, LogContextKeys.STATUS_CODE, 0)

            if status_code == HTTPStatusCodes.TOO_MANY_REQUESTS:
                # Handle rate limiting
                retry_after = self._extract_retry_after(exception.response)
                self.state_machine.handle_429(retry_after)

                # Wait for retry delay
                retry_delay = self.state_machine.get_retry_delay()
                if retry_delay > 0:
                    await asyncio.sleep(retry_delay)

                # Reset rate limiter on 429
                self.rate_limiter.reset()

            elif HTTPStatusCodes.is_server_error(status_code):
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
                message=f"{error_message} (after {self.config.api.tmdb.retry_attempts} retries)",
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

    def _convert_tmdb_exception(
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
            status_code = getattr(exception.response, LogContextKeys.STATUS_CODE, 0)

            if status_code == HTTPStatusCodes.UNAUTHORIZED:
                return (
                    ErrorCode.TMDB_API_AUTHENTICATION_ERROR,
                    TMDBErrorMessages.AUTHENTICATION_FAILED,
                )
            if status_code == HTTPStatusCodes.FORBIDDEN:
                return (
                    ErrorCode.TMDB_API_AUTHENTICATION_ERROR,
                    TMDBErrorMessages.ACCESS_FORBIDDEN,
                )
            if status_code == HTTPStatusCodes.TOO_MANY_REQUESTS:
                return (
                    ErrorCode.TMDB_API_RATE_LIMIT_EXCEEDED,
                    TMDBErrorMessages.RATE_LIMIT_EXCEEDED,
                )
            if HTTPStatusCodes.is_client_error(status_code):
                return (
                    ErrorCode.TMDB_API_REQUEST_FAILED,
                    TMDBErrorMessages.CLIENT_ERROR.format(status_code=status_code),
                )
            if HTTPStatusCodes.is_server_error(status_code):
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
