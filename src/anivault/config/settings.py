"""
AniVault Settings Configuration

This module defines Pydantic models for application configuration,
including filter settings for the smart filtering engine.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator

from anivault.shared.constants import (
    ADDITIONAL_VIDEO_FORMATS,
    ANIVAULT_HOME_DIR,
    APPLICATION_NAME,
    APPLICATION_VERSION,
    BOOLEAN_TRUE_STRING,
    DEFAULT_BATCH_SIZE_LARGE,
    DEFAULT_CACHE_BACKEND,
    DEFAULT_CACHE_MAX_SIZE,
    DEFAULT_CACHE_TTL,
    DEFAULT_CONCURRENT_REQUESTS,
    DEFAULT_CPU_LIMIT,
    DEFAULT_ENCODING,
    DEFAULT_LOG_BACKUP_COUNT,
    DEFAULT_LOG_FILE_PATH,
    DEFAULT_LOG_MAX_BYTES,
    DEFAULT_MEMORY_LIMIT_STRING,
    DEFAULT_MIN_FILE_SIZE_MB,
    DEFAULT_PARALLEL_THRESHOLD,
    DEFAULT_PROFILING_FILE_PATH,
    DEFAULT_TIMEOUT,
    DEFAULT_TMDB_RATE_LIMIT_DELAY,
    DEFAULT_TMDB_RATE_LIMIT_RPS,
    DEFAULT_TMDB_RETRY_ATTEMPTS,
    DEFAULT_TMDB_RETRY_DELAY,
    DEFAULT_TMDB_TIMEOUT,
    DEFAULT_VERSION_STRING,
    DEFAULT_WORKERS,
    EXCLUDED_DIRECTORY_PATTERNS,
    EXCLUDED_FILENAME_PATTERNS,
    SUBTITLE_EXTENSIONS,
    SUPPORTED_VIDEO_EXTENSIONS,
    TMDB_API_BASE_URL,
)


class FilterConfig(BaseModel):
    """Configuration for the smart filtering engine."""

    # File extension filtering
    allowed_extensions: list[str] = Field(
        default=list(SUPPORTED_VIDEO_EXTENSIONS)
        + ADDITIONAL_VIDEO_FORMATS
        + SUBTITLE_EXTENSIONS,
        description="List of allowed file extensions including video and subtitle files",
    )

    # File size filtering
    min_file_size_mb: int = Field(
        default=DEFAULT_MIN_FILE_SIZE_MB,
        ge=0,
        description="Minimum file size in MB to include in scan",
    )

    # Filename pattern exclusion
    excluded_filename_patterns: list[str] = Field(
        default=EXCLUDED_FILENAME_PATTERNS,
        description="Filename patterns to exclude from scanning",
    )

    # Directory pattern exclusion
    excluded_dir_patterns: list[str] = Field(
        default=EXCLUDED_DIRECTORY_PATTERNS,
        description="Directory patterns to exclude from scanning",
    )

    # Hidden file/directory filtering
    skip_hidden_files: bool = Field(
        default=True,
        description="Skip files and directories starting with '.'",
    )

    # System file filtering
    skip_system_files: bool = Field(
        default=True,
        description="Skip system files and directories",
    )

    @field_validator("allowed_extensions")
    @classmethod
    def validate_extensions(cls, v: list[str]) -> list[str]:
        """Validate that extensions start with a dot."""
        for ext in v:
            if not ext.startswith("."):
                msg = f"Extension '{ext}' must start with a dot"
                raise ValueError(msg)
        return v

    @field_validator("excluded_filename_patterns", "excluded_dir_patterns")
    @classmethod
    def validate_patterns(cls, v: list[str]) -> list[str]:
        """Validate that patterns are non-empty strings."""
        for pattern in v:
            if not isinstance(pattern, str) or not pattern.strip():
                raise ValueError("Patterns must be non-empty strings")
        return v


class ScanConfig(BaseModel):
    """Configuration for directory scanning."""

    # Supported file extensions (legacy compatibility)
    supported_extensions: list[str] = Field(
        default=[
            # Video files
            ".mkv",
            ".mp4",
            ".avi",
            ".mov",
            ".wmv",
            ".flv",
            ".m4v",
            ".webm",
            ".m2ts",
            ".ts",
            # Subtitle files
            ".srt",
            ".ass",
            ".ssa",
            ".sub",
            ".idx",
            ".vtt",
            ".smi",
            ".sami",
            ".mks",
            ".sup",
            ".pgs",
            ".dvb",
        ],
        description="Supported file extensions for scanning including video and subtitle files",
    )

    # Batch processing settings
    batch_size: int = Field(
        default=DEFAULT_BATCH_SIZE_LARGE,
        gt=0,
        description="Number of files to process in each batch",
    )

    # Worker settings
    max_workers: int = Field(
        default=DEFAULT_WORKERS,
        gt=0,
        description="Maximum number of worker threads",
    )

    # Timeout settings
    timeout: int = Field(
        default=DEFAULT_TIMEOUT,
        gt=0,
        description="Timeout in seconds for file processing",
    )

    # Parallel scanning settings
    enable_parallel_scanning: bool = Field(
        default=True,
        description="Enable parallel directory scanning",
    )

    parallel_threshold: int = Field(
        default=DEFAULT_PARALLEL_THRESHOLD,
        gt=0,
        description="Minimum file count to use parallel scanning",
    )

    # Filter configuration
    filter: FilterConfig = Field(
        default_factory=FilterConfig,
        description="Smart filtering configuration",
    )

    @field_validator("supported_extensions")
    @classmethod
    def validate_supported_extensions(cls, v: list[str]) -> list[str]:
        """Validate that extensions start with a dot."""
        for ext in v:
            if not ext.startswith("."):
                msg = f"Extension '{ext}' must start with a dot"
                raise ValueError(msg)
        return v


class AppConfig(BaseModel):
    """Application configuration."""

    name: str = Field(default=APPLICATION_NAME, description="Application name")
    version: str = Field(default=APPLICATION_VERSION, description="Application version")
    description: str = Field(
        default="Anime Collection Management System",
        description="Application description",
    )
    debug: bool = Field(default=False, description="Enable debug mode")


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )
    file: str = Field(default=DEFAULT_LOG_FILE_PATH, description="Log file path")
    max_bytes: int = Field(
        default=DEFAULT_LOG_MAX_BYTES,
        description="Maximum log file size in bytes",  # 10MB
    )
    backup_count: int = Field(
        default=DEFAULT_LOG_BACKUP_COUNT,
        description="Number of backup log files to keep",
    )
    console_output: bool = Field(default=True, description="Enable console logging")


class TMDBConfig(BaseModel):
    """TMDB API configuration."""

    base_url: str = Field(
        default=TMDB_API_BASE_URL,
        description="TMDB API base URL",
    )
    api_key: str = Field(
        default="",
        description="TMDB API key (required for API access)",
    )
    timeout: int = Field(
        default=DEFAULT_TMDB_TIMEOUT,
        gt=0,
        description="Request timeout in seconds",
    )
    retry_attempts: int = Field(
        default=DEFAULT_TMDB_RETRY_ATTEMPTS,
        ge=0,
        description="Number of retry attempts",
    )
    retry_delay: float = Field(
        default=DEFAULT_TMDB_RETRY_DELAY,
        ge=0,
        description="Delay between retries in seconds",
    )
    rate_limit_delay: float = Field(
        default=DEFAULT_TMDB_RATE_LIMIT_DELAY,
        ge=0,
        description="Delay between requests in seconds",
    )
    rate_limit_rps: float = Field(
        default=DEFAULT_TMDB_RATE_LIMIT_RPS,
        gt=0,
        description="Rate limit in requests per second",
    )
    concurrent_requests: int = Field(
        default=DEFAULT_CONCURRENT_REQUESTS,
        gt=0,
        description="Maximum number of concurrent requests",
    )


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = Field(default=True, description="Enable caching")
    ttl: int = Field(
        default=DEFAULT_CACHE_TTL,
        gt=0,
        description="Cache time-to-live in seconds",
    )
    max_size: int = Field(
        default=DEFAULT_CACHE_MAX_SIZE,
        gt=0,
        description="Maximum cache size",
    )
    backend: str = Field(
        default=DEFAULT_CACHE_BACKEND,
        description="Cache backend (memory, redis, sqlite)",
    )


class PerformanceConfig(BaseModel):
    """Performance configuration."""

    memory_limit: str = Field(
        default=DEFAULT_MEMORY_LIMIT_STRING,
        description="Memory limit for the application",
    )
    cpu_limit: int = Field(
        default=DEFAULT_CPU_LIMIT,
        gt=0,
        description="CPU limit for the application",
    )
    enable_profiling: bool = Field(
        default=False,
        description="Enable performance profiling",
    )
    profile_output: str = Field(
        default=DEFAULT_PROFILING_FILE_PATH,
        description="Profiling output file path",
    )


class Settings(BaseModel):
    """Main settings model containing all configuration sections."""

    model_config = ConfigDict(
        # Optimize JSON serialization for settings performance
        json_encoders={
            # Custom encoders for specific types if needed
        },
        # Use orjson for better performance in settings serialization
        json_schema_extra={
            "example": {
                "app": {"name": "AniVault", "version": "1.0.0", "debug": False},
                "logging": {"level": "INFO", "format": "json"},
                "tmdb": {"api_key": "your_api_key", "base_url": "https://api.themoviedb.org/3"},
                "file_processing": {"max_workers": 4, "supported_extensions": [".mkv", ".mp4"]},
                "cache": {"enabled": True, "ttl_seconds": 604800},
                "performance": {"profiling_enabled": False}
            }
        }
    )

    app: AppConfig = Field(default_factory=AppConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    tmdb: TMDBConfig = Field(default_factory=TMDBConfig)
    file_processing: ScanConfig = Field(default_factory=ScanConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)

    @classmethod
    def from_yaml_file(cls, file_path: str | Path) -> Settings:
        """Load settings from a YAML file.

        Args:
            file_path: Path to the YAML configuration file

        Returns:
            Settings instance loaded from the file

        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            yaml.YAMLError: If the YAML file is malformed
            ValidationError: If the configuration doesn't match the schema
        """
        file_path = Path(file_path)

        if not file_path.exists():
            msg = f"Configuration file not found: {file_path}"
            raise FileNotFoundError(msg)

        with open(file_path, encoding=DEFAULT_ENCODING) as f:
            data = yaml.safe_load(f)

        return cls.model_validate(data)

    @classmethod
    def from_environment(cls) -> Settings:
        """Load settings from environment variables.

        Returns:
            Settings instance with values from environment variables
        """
        return cls.model_validate(
            {
                "app": {
                    "name": os.getenv("ANIVAULT_NAME", "AniVault"),
                    "version": os.getenv("ANIVAULT_VERSION", DEFAULT_VERSION_STRING),
                    "debug": os.getenv("ANIVAULT_DEBUG", "false").lower() == "true",
                },
                "logging": {
                    "level": os.getenv("ANIVAULT_LOG_LEVEL", "INFO"),
                    "console_output": os.getenv("ANIVAULT_LOG_CONSOLE", "true").lower()
                    == "true",
                },
                "tmdb": {
                    "base_url": os.getenv(
                        "TMDB_BASE_URL",
                        TMDB_API_BASE_URL,
                    ),
                    "api_key": os.getenv("TMDB_API_KEY", ""),
                    "timeout": int(
                        os.getenv("TMDB_TIMEOUT", str(DEFAULT_TMDB_TIMEOUT)),
                    ),
                    "retry_attempts": int(
                        os.getenv(
                            "TMDB_RETRY_ATTEMPTS",
                            str(DEFAULT_TMDB_RETRY_ATTEMPTS),
                        ),
                    ),
                    "retry_delay": float(
                        os.getenv("TMDB_RETRY_DELAY", str(DEFAULT_TMDB_RETRY_DELAY)),
                    ),
                    "rate_limit_delay": float(
                        os.getenv(
                            "TMDB_RATE_LIMIT_DELAY",
                            str(DEFAULT_TMDB_RATE_LIMIT_DELAY),
                        ),
                    ),
                    "rate_limit_rps": float(
                        os.getenv(
                            "TMDB_RATE_LIMIT_RPS",
                            str(DEFAULT_TMDB_RATE_LIMIT_RPS),
                        ),
                    ),
                    "concurrent_requests": int(
                        os.getenv(
                            "TMDB_CONCURRENT_REQUESTS",
                            str(DEFAULT_CONCURRENT_REQUESTS),
                        ),
                    ),
                },
                "file_processing": {
                    "max_workers": int(
                        os.getenv("ANIVAULT_MAX_WORKERS", str(DEFAULT_WORKERS)),
                    ),
                    "enable_parallel_scanning": os.getenv(
                        "ANIVAULT_PARALLEL_SCAN",
                        "true",
                    ).lower()
                    == "true",
                    "parallel_threshold": int(
                        os.getenv(
                            "ANIVAULT_PARALLEL_THRESHOLD",
                            str(DEFAULT_PARALLEL_THRESHOLD),
                        ),
                    ),
                },
                "cache": {
                    "enabled": os.getenv(
                        "ANIVAULT_CACHE_ENABLED",
                        BOOLEAN_TRUE_STRING,
                    ).lower()
                    == BOOLEAN_TRUE_STRING,
                    "ttl": int(os.getenv("ANIVAULT_CACHE_TTL", str(DEFAULT_CACHE_TTL))),
                },
            },
        )

    def to_yaml_file(self, file_path: str | Path) -> None:
        """Save settings to a YAML file.

        Args:
            file_path: Path where to save the YAML configuration file
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding=DEFAULT_ENCODING) as f:
            yaml.dump(
                self.model_dump(exclude_defaults=True),
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )


def load_settings(config_path: str | Path | None = None) -> Settings:
    """Load settings from configuration file or environment.

    Args:
        config_path: Optional path to configuration file. If None, tries to load
                    from default locations or environment variables.

    Returns:
        Settings instance loaded from the specified source
    """
    if config_path:
        return Settings.from_yaml_file(config_path)

    # Try to load from default configuration file
    default_config_paths = [
        Path("config/settings.yaml"),
        Path("settings.yaml"),
        Path.home() / ANIVAULT_HOME_DIR / "settings.yaml",
    ]

    for config_path in default_config_paths:
        if config_path.exists():
            return Settings.from_yaml_file(config_path)

    # Fall back to environment variables
    return Settings.from_environment()


# Global settings instance
_settings: Settings | None = None


def get_config() -> Settings:
    """Get the global settings instance.

    Returns:
        The global Settings instance, loading it if necessary.
    """
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings
