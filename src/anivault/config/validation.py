"""
Configuration validation models for AniVault.

This module defines Pydantic models for validating the structure of the
`anivault.toml` configuration file. Each model represents a section of the
configuration file and provides type validation and default values.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from anivault.shared.constants import (
    TMDB,
    Application,
    Config,
    LogLevels,
    RunDefaults,
    Timeout,
    TMDBConfig,
)


class AppSettings(BaseModel):
    """Application-level settings."""

    name: str = Field(default=Application.NAME, description="Application name")
    version: str = Field(default=Application.VERSION, description="Application version")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str | int = Field(
        default=LogLevels.DEFAULT,
        description="Logging level",
    )
    max_workers: int = Field(
        default=RunDefaults.DEFAULT_MAX_WORKERS,
        ge=1,
        le=16,
        description="Maximum worker threads",
    )


class TmdbSettings(BaseModel):
    """TMDB API settings."""

    api_key: str = Field(default="", description="TMDB API key")
    base_url: str = Field(
        default=TMDB.API_BASE_URL,
        description="TMDB API base URL",
    )
    language: str = Field(
        default="ko-KR",
        description="Preferred language for API responses",
    )
    timeout: int = Field(
        default=Timeout.TMDB,
        ge=1,
        le=300,
        description="Request timeout in seconds",
    )
    rate_limit: int = Field(
        default=TMDBConfig.RATE_LIMIT_RPS,
        ge=1,
        le=50,
        description="Requests per second limit",
    )

    model_config = ConfigDict(
        validate_assignment=True,  # Validate on assignment
    )

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate TMDB API key."""
        if not v or v.strip() == "":
            raise ValueError("TMDB API key is required")
        return v


class SecuritySettings(BaseModel):
    """Security-related settings."""

    enable_encryption: bool = Field(
        default=True,
        description="Enable encryption for sensitive data",
    )
    key_rotation_days: int = Field(
        default=90,
        ge=1,
        le=365,
        description="Key rotation interval in days",
    )
    max_pin_attempts: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum PIN attempts before lockout",
    )
    lockout_duration_minutes: int = Field(
        default=30,
        ge=1,
        le=1440,
        description="Lockout duration in minutes",
    )


class CacheSettings(BaseModel):
    """Cache-related settings."""

    enabled: bool = Field(default=True, description="Enable caching")
    ttl_hours: int = Field(default=720, ge=1, le=8760, description="Cache TTL in hours")
    max_size_mb: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum cache size in MB",
    )
    cleanup_interval_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Cache cleanup interval in hours",
    )


class PerformanceSettings(BaseModel):
    """Performance-related settings."""

    scan_batch_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Batch size for directory scanning",
    )
    parse_batch_size: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Batch size for file parsing",
    )
    memory_limit_mb: int = Field(
        default=500,
        ge=100,
        le=2000,
        description="Memory usage limit in MB",
    )
    enable_profiling: bool = Field(
        default=False,
        description="Enable performance profiling",
    )


class FolderSettings(BaseModel):
    """Folder and directory settings."""

    source_folder: str = Field(
        default="",
        description="Source folder path for media files to organize",
    )
    target_folder: str = Field(
        default="",
        description="Target folder path for organized media files",
    )
    auto_scan_on_startup: bool = Field(
        default=False,
        description="Automatically scan source folder when application starts",
    )
    auto_scan_interval_minutes: int = Field(
        default=0,
        ge=0,
        le=1440,
        description="Auto scan interval in minutes (0 = disabled)",
    )
    include_subdirectories: bool = Field(
        default=True,
        description="Include subdirectories when scanning",
    )

    model_config = ConfigDict(
        validate_assignment=True,
    )

    @field_validator("source_folder", "target_folder")
    @classmethod
    def validate_folder_path(cls, v: str) -> str:
        """Validate folder path."""
        if v and v.strip():
            path = Path(v.strip())
            # Basic validation - path should be absolute or resolvable
            try:
                resolved_path = path.resolve()
                # Check if it's a valid path format
                if not resolved_path.is_absolute():
                    raise ValueError("Folder path must be absolute")
            except (OSError, ValueError) as e:
                msg = f"Invalid folder path: {e}"
                raise ValueError(msg) from e
        return v

    @field_validator("auto_scan_interval_minutes")
    @classmethod
    def validate_scan_interval(cls, v: int) -> int:
        """Validate scan interval."""
        if v < 0:
            raise ValueError("Scan interval must be non-negative")
        if v > 0 and v < 1:
            raise ValueError("Scan interval must be at least 1 minute")
        return v


class TomlConfig(BaseSettings):
    """Main configuration model that aggregates all sections."""

    app: AppSettings = Field(
        default_factory=AppSettings,
        description="Application settings",
    )
    tmdb: TmdbSettings = Field(
        default_factory=TmdbSettings,
        description="TMDB API settings",
    )
    security: SecuritySettings = Field(
        default_factory=SecuritySettings,
        description="Security settings",
    )
    cache: CacheSettings = Field(
        default_factory=CacheSettings,
        description="Cache settings",
    )
    performance: PerformanceSettings = Field(
        default_factory=PerformanceSettings,
        description="Performance settings",
    )
    folders: FolderSettings = Field(
        default_factory=FolderSettings,
        description="Folder and directory settings",
    )

    model_config = SettingsConfigDict(
        extra="forbid",  # Reject extra fields
        validate_assignment=True,  # Validate on assignment
        use_enum_values=True,  # Use enum values in serialization
        env_prefix=Config.ENV_PREFIX,  # Environment variable prefix
        env_nested_delimiter=Config.ENV_DELIMITER,  # Nested field delimiter for env vars
        env_ignore_empty=True,  # Ignore empty environment variables
        # JSON serialization optimization with orjson
        json_encoders={
            # Custom encoders for specific types if needed
        },
        # Use orjson for better performance
        json_schema_extra={
            "example": {
                "app": {"name": "AniVault", "version": "1.0.0"},
                "tmdb": {"api_key": "your_api_key"},
                "security": {"encryption_enabled": True},
                "cache": {"enabled": True},
                "performance": {"profiling_enabled": False},
                "folders": {
                    "source_folder": "/path/to/source",
                    "target_folder": "/path/to/target",
                    "auto_scan_on_startup": True,
                    "auto_scan_interval_minutes": 60,
                },
            },
        },
    )
