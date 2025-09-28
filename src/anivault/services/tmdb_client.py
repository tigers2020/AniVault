"""TMDB API client with rate limiting and error handling."""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from tmdbv3api import TV, Movie, TMDb
from urllib3.util.retry import Retry

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # dotenv not available, skip loading
    pass


logger = logging.getLogger(__name__)


class TokenBucket:
    """Thread-safe token bucket implementation for rate limiting."""

    def __init__(self, capacity: float, refill_rate: float) -> None:
        """Initialize token bucket.

        Args:
            capacity: Maximum number of tokens in the bucket
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = threading.Lock()

    def consume(self, tokens: float = 1.0) -> bool:
        """Try to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        with self.lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def wait_for_tokens(
        self,
        tokens: float = 1.0,
        timeout: float | None = None,
    ) -> bool:
        """Wait until enough tokens are available.

        Args:
            tokens: Number of tokens needed
            timeout: Maximum time to wait in seconds

        Returns:
            True if tokens became available, False if timeout
        """
        start_time = time.time()

        while True:
            if self.consume(tokens):
                return True

            if timeout is not None and (time.time() - start_time) >= timeout:
                return False

            # Calculate wait time for next refill
            with self.lock:
                self._refill()
                if self.tokens >= tokens:
                    continue
                # Calculate time until enough tokens are available
                needed_tokens = tokens - self.tokens
                wait_time = needed_tokens / self.refill_rate
                # Add small buffer to avoid race conditions
                wait_time = max(0.001, min(wait_time, 1.0))

            time.sleep(wait_time)

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now


class RateLimitState(Enum):
    """Rate limiting state machine states."""

    NORMAL = "normal"
    THROTTLE = "throttle"
    CACHE_ONLY = "cache_only"
    SLEEP_THEN_RESUME = "sleep_then_resume"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    max_requests_per_second: float = 35.0  # Conservative limit (TMDB ~50 rps)
    max_concurrent_requests: int = 4
    retry_after_respect: bool = True
    exponential_backoff: bool = True
    max_retries: int = 3
    circuit_breaker_threshold: float = 0.6  # 60% failure rate
    circuit_breaker_timeout: int = 300  # 5 minutes
    # Token bucket configuration
    token_bucket_capacity: float = 35.0  # Burst capacity
    token_bucket_refill_rate: float = 35.0  # Tokens per second
    token_timeout: float = 30.0  # Max wait time for tokens


@dataclass
class TMDBConfig:
    """Configuration for TMDB API client."""

    api_key: str = field(default_factory=lambda: os.getenv("TMDB_API_KEY", ""))
    base_url: str = "https://api.themoviedb.org/3"
    timeout: int = 30
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.api_key:
            error_msg = (
                "TMDB_API_KEY is required. Set it in environment variables "
                "or pass it directly."
            )
            raise ValueError(error_msg)


class TMDBClient:
    """Enhanced TMDB API client with rate limiting and error handling."""

    def __init__(self, config: TMDBConfig):
        """Initialize the TMDB client.

        Args:
            config: TMDB configuration including API key and rate limiting settings
        """
        self.config = config
        self.rate_limit_state = RateLimitState.NORMAL
        self.request_count = 0
        self.last_request_time = 0.0
        self.failure_count = 0
        self.total_requests = 0
        self.circuit_breaker_start = None

        # Initialize token bucket for rate limiting
        self.token_bucket = TokenBucket(
            capacity=config.rate_limit.token_bucket_capacity,
            refill_rate=config.rate_limit.token_bucket_refill_rate,
        )

        # Initialize semaphore for concurrent request limiting
        self.semaphore = threading.Semaphore(config.rate_limit.max_concurrent_requests)

        # Initialize TMDB API
        self.tmdb = TMDb()
        self.tmdb.api_key = config.api_key
        self.tmdb.language = "en-US"

        # Initialize API objects
        self.tv = TV()
        self.movie = Movie()

        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=config.rate_limit.max_retries,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.info(
            "TMDB client initialized with token bucket rate limit: %.1f rps, capacity: %.1f",
            config.rate_limit.token_bucket_refill_rate,
            config.rate_limit.token_bucket_capacity,
        )

    def get_rate_limit_state(self) -> RateLimitState:
        """Get current rate limiting state.

        Returns:
            Current rate limiting state
        """
        return self.rate_limit_state

    def reset_rate_limit_state(self) -> None:
        """Reset rate limiting state to NORMAL."""
        self.rate_limit_state = RateLimitState.NORMAL
        self.failure_count = 0
        self.circuit_breaker_start = None
        logger.info("Rate limiting state reset to NORMAL")

    def get_stats(self) -> dict[str, Any]:
        """Get current client statistics.

        Returns:
            Dictionary containing client statistics
        """
        return {
            "rate_limit_state": self.rate_limit_state.value,
            "total_requests": self.total_requests,
            "failure_count": self.failure_count,
            "failure_rate": self.failure_count / max(1, self.total_requests),
            "tokens_available": self.token_bucket.tokens,
            "semaphore_available": self.semaphore._value,
        }

    def _check_rate_limit(self) -> bool:
        """Check if we can make a request based on token bucket rate limiting.

        Returns:
            True if request can be made, False if we need to wait
        """
        # Wait for token from bucket
        if not self.token_bucket.wait_for_tokens(
            timeout=self.config.rate_limit.token_timeout,
        ):
            logger.warning(
                "Rate limit timeout: no tokens available within timeout period",
            )
            return False

        # Acquire semaphore for concurrent request limiting
        self.semaphore.acquire()

        return True

    def _handle_429_error(self, response: requests.Response) -> None:
        """Handle HTTP 429 (Too Many Requests) error.

        Args:
            response: The HTTP response that returned 429
        """
        self.rate_limit_state = RateLimitState.THROTTLE

        # Respect Retry-After header if present (highest priority)
        retry_after = response.headers.get("Retry-After")
        if retry_after and self.config.rate_limit.retry_after_respect:
            try:
                wait_time = float(retry_after)
                logger.warning(
                    "Rate limited: waiting %ds (Retry-After header)",
                    wait_time,
                )
                # Clear token bucket to prevent immediate retry
                with self.token_bucket.lock:
                    self.token_bucket.tokens = 0
                    self.token_bucket.last_refill = time.time()
                time.sleep(wait_time)
                return
            except ValueError:
                logger.warning("Invalid Retry-After header: %s", retry_after)

        # Fallback to exponential backoff
        wait_time = 2 ** min(self.failure_count, 5)
        logger.warning("Rate limited: exponential backoff %ds", wait_time)
        # Clear token bucket to prevent immediate retry
        with self.token_bucket.lock:
            self.token_bucket.tokens = 0
            self.token_bucket.last_refill = time.time()
        time.sleep(wait_time)

        self.failure_count += 1

    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker should be activated.

        Returns:
            True if circuit breaker is open (should not make requests)
        """
        if self.circuit_breaker_start is None:
            return False

        # Check if circuit breaker timeout has passed
        if (
            time.time() - self.circuit_breaker_start
            > self.config.rate_limit.circuit_breaker_timeout
        ):
            logger.info("Circuit breaker timeout expired, attempting to close")
            self.circuit_breaker_start = None
            self.failure_count = 0
            self.rate_limit_state = RateLimitState.NORMAL
            return False

        return True

    def _update_circuit_breaker(self, *, success: bool) -> None:
        """Update circuit breaker state based on request success.

        Args:
            success: Whether the request was successful
        """
        self.total_requests += 1

        if not success:
            self.failure_count += 1
        # Reset failure count on success to allow recovery
        elif self.rate_limit_state in [
            RateLimitState.THROTTLE,
            RateLimitState.SLEEP_THEN_RESUME,
        ]:
            self.failure_count = max(0, self.failure_count - 1)

        # Check if we should open circuit breaker
        min_requests_for_circuit_breaker = 10
        if (
            self.total_requests > min_requests_for_circuit_breaker
            and self.failure_count / self.total_requests
            > self.config.rate_limit.circuit_breaker_threshold
        ):
            if self.circuit_breaker_start is None:
                failure_rate = self.failure_count / self.total_requests
                logger.warning(
                    "Circuit breaker opened: failure rate %.2f%%",
                    failure_rate * 100,
                )
                self.circuit_breaker_start = time.time()
                self.rate_limit_state = RateLimitState.CACHE_ONLY
        elif success and self.rate_limit_state == RateLimitState.THROTTLE:
            # Transition from THROTTLE to SLEEP_THEN_RESUME on success
            self.rate_limit_state = RateLimitState.SLEEP_THEN_RESUME
            logger.info("Transitioning from THROTTLE to SLEEP_THEN_RESUME")
        elif success and self.rate_limit_state == RateLimitState.SLEEP_THEN_RESUME:
            # Transition from SLEEP_THEN_RESUME to NORMAL after successful requests
            self.rate_limit_state = RateLimitState.NORMAL
            logger.info("Transitioning from SLEEP_THEN_RESUME to NORMAL")

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make a rate-limited request to TMDB API.

        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            HTTP response

        Raises:
            requests.RequestException: If request fails
        """
        # Check circuit breaker
        if self._check_circuit_breaker():
            error_msg = "Circuit breaker is open"
            raise requests.RequestException(error_msg)

        # Check rate limit and acquire semaphore
        if not self._check_rate_limit():
            error_msg = "Rate limit check failed"
            raise requests.RequestException(error_msg)

        # Make request
        try:
            response = self.session.request(
                method,
                url,
                timeout=self.config.timeout,
                **kwargs,
            )

            # Handle rate limiting
            http_too_many_requests = 429
            if response.status_code == http_too_many_requests:
                self._handle_429_error(response)
                self._update_circuit_breaker(success=False)
                error_msg = f"Rate limited: {response.status_code}"
                raise requests.RequestException(error_msg)

            # Update state
            self.last_request_time = time.time()
            self.request_count += 1

            http_bad_request = 400
            if response.status_code >= http_bad_request:
                self._update_circuit_breaker(success=False)
                response.raise_for_status()
            else:
                self._update_circuit_breaker(success=True)
                self.rate_limit_state = RateLimitState.NORMAL

            return response

        except requests.RequestException:
            self._update_circuit_breaker(success=False)
            logger.exception("Request failed")
            raise
        finally:
            # Always release semaphore
            self.semaphore.release()

    def search_tv(self, query: str, page: int = 1) -> dict[str, Any]:
        """Search for TV shows.

        Args:
            query: Search query
            page: Page number

        Returns:
            Search results
        """
        try:
            results = self.tv.search(query, page=page)
            logger.debug(
                "TV search successful: %d results for '%s'",
                len(results),
                query,
            )
            return results
        except Exception:
            logger.exception("TV search failed")
            raise

    def get_tv_details(self, tv_id: int) -> dict[str, Any]:
        """Get TV show details.

        Args:
            tv_id: TV show ID

        Returns:
            TV show details
        """
        try:
            details = self.tv.details(tv_id)
            logger.debug("TV details retrieved for ID %d", tv_id)
            return details
        except Exception:
            logger.exception("TV details failed")
            raise

    def search_movie(self, query: str, page: int = 1) -> dict[str, Any]:
        """Search for movies.

        Args:
            query: Search query
            page: Page number

        Returns:
            Search results
        """
        try:
            results = self.movie.search(query, page=page)
            logger.debug(
                "Movie search successful: %d results for '%s'",
                len(results),
                query,
            )
            return results
        except Exception:
            logger.exception("Movie search failed")
            raise

    def get_movie_details(self, movie_id: int) -> dict[str, Any]:
        """Get movie details.

        Args:
            movie_id: Movie ID

        Returns:
            Movie details
        """
        try:
            details = self.movie.details(movie_id)
            logger.debug("Movie details retrieved for ID %d", movie_id)
            return details
        except Exception:
            logger.exception("Movie details failed")
            raise

    def get_rate_limit_status(self) -> dict[str, Any]:
        """Get current rate limiting status.

        Returns:
            Rate limiting status information
        """
        return {
            "state": self.rate_limit_state.value,
            "request_count": self.request_count,
            "failure_count": self.failure_count,
            "total_requests": self.total_requests,
            "failure_rate": self.failure_count / max(self.total_requests, 1),
            "circuit_breaker_open": self.circuit_breaker_start is not None,
            "last_request_time": self.last_request_time,
        }

    def reset_rate_limit(self) -> None:
        """Reset rate limiting state."""
        self.rate_limit_state = RateLimitState.NORMAL
        self.failure_count = 0
        self.circuit_breaker_start = None
        logger.info("Rate limiting state reset")

    def close(self) -> None:
        """Close the client and cleanup resources."""
        self.session.close()
        logger.info("TMDB client closed")
