"""API configuration models (TMDB, etc.).

This module contains configuration models for external API services,
primarily TMDB (The Movie Database) API settings.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from anivault.shared.constants import (
    APIConfig,
    Timeout,
)
from anivault.shared.constants import TMDBConfig as TMDBConstants
from anivault.shared.constants import (
    TMDBErrorHandling,
)


class TMDBSettings(BaseModel):
    """TMDB API configuration.

    This class manages TMDB API settings including authentication,
    rate limiting, retry behavior, and request timeouts.

    Note: base_url is managed internally by tmdbv3api library.

    Security: api_key is masked in __repr__ and excluded from model_dump
    to prevent accidental exposure in logs or serialization.
    """

    # API authentication (sensitive - hidden from repr)
    api_key: str = Field(
        default="",
        repr=False,  # Security: hide from logs/repr
        description="TMDB API key (required for API access)",
    )

    # Request settings
    timeout: int = Field(
        default=Timeout.TMDB,
        gt=0,
        description="Request timeout in seconds",
    )

    # Retry settings
    retry_attempts: int = Field(
        default=TMDBErrorHandling.RETRY_ATTEMPTS,
        ge=0,
        description="Number of retry attempts",
    )
    retry_delay: float = Field(
        default=TMDBErrorHandling.RETRY_DELAY,
        ge=0,
        description="Delay between retries in seconds",
    )

    # Rate limiting settings
    rate_limit_delay: float = Field(
        default=TMDBErrorHandling.RATE_LIMIT_DELAY,
        ge=0,
        description="Delay between requests in seconds",
    )
    rate_limit_rps: float = Field(
        default=TMDBConstants.RATE_LIMIT_RPS,
        gt=0,
        description="Rate limit in requests per second",
    )

    # Concurrency settings
    concurrent_requests: int = Field(
        default=APIConfig.DEFAULT_CONCURRENT_REQUESTS,
        gt=0,
        description="Maximum number of concurrent requests",
    )

    def __repr__(self) -> str:
        """Custom repr that masks sensitive api_key.

        Security: Masks API key in logs and debugging output while
        allowing normal serialization for config file storage.

        Design rationale:
        - Logs: Mask API key (security)
        - Config files: Include API key (functionality)
        - File permissions: OS-level protection

        Returns a safe representation suitable for logging and debugging
        without exposing the actual API key value.
        """
        masked_key = "****" if self.api_key else "[empty]"
        return (
            f"TMDBSettings("
            f"api_key={masked_key}, "
            f"timeout={self.timeout}, "
            f"retry_attempts={self.retry_attempts}, "
            f"rate_limit_rps={self.rate_limit_rps})"
        )


class APISettings(BaseModel):
    """API configuration container.

    This class serves as a container for all external API configurations.
    Currently contains TMDB settings, with room for future API expansions.

    Note: Environment variable loading is handled by the parent Settings class.
    """

    tmdb: TMDBSettings = Field(
        default_factory=TMDBSettings,
        description="TMDB API configuration",
    )


# Backward compatibility alias
TMDBConfig = TMDBSettings


__all__ = [
    "APISettings",
    "TMDBConfig",  # Backward compatibility
    "TMDBSettings",
]
