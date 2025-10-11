"""
AniVault Settings Configuration

This module defines Pydantic models for application configuration,
including filter settings for the smart filtering engine.
"""

from __future__ import annotations

import logging
import os
import threading
import typing
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from anivault.shared.constants import (
    APIConfig,
    Application,
    Batch,
    Cache,
    Encoding,
    ExclusionPatterns,
    FileSystem,
    Logging,
    Memory,
    SubtitleFormats,
    Timeout,
)
from anivault.shared.constants import TMDBConfig as TMDBConstants
from anivault.shared.constants import (
    TMDBErrorHandling,
    VideoFormats,
    WorkerConfig,
)

logger = logging.getLogger(__name__)

# Type Safety Feature Flags
# -------------------------
# These flags control gradual migration from dict/Any to typed Pydantic models.
# WARNING: DO NOT change these values in production without thorough testing.

USE_LEGACY_DICT_TYPES: typing.Final[bool] = False
"""Enable legacy dict/Any types for backward compatibility.

This flag supports gradual migration from untyped dict structures
to type-safe Pydantic models. When False (default), the application
uses strict type checking with Pydantic models.

Security Note:
    Setting this to True disables type safety guarantees and should
    ONLY be used during migration phases with appropriate safeguards.
    The default False value follows the "secure by default" principle.

Default: False (type-safe mode)
Recommended: Keep False in production environments
"""


class FilterConfig(BaseModel):
    """Configuration for the smart filtering engine."""

    # File extension filtering
    allowed_extensions: list[str] = Field(
        default=list(VideoFormats.ALL_EXTENSIONS)
        + FileSystem.ADDITIONAL_VIDEO_FORMATS
        + SubtitleFormats.EXTENSIONS,
        description="List of allowed file extensions including video and subtitle files",
    )

    # File size filtering
    min_file_size_mb: int = Field(
        default=Logging.MIN_FILE_SIZE_MB,
        ge=0,
        description="Minimum file size in MB to include in scan",
    )

    # Filename pattern exclusion
    excluded_filename_patterns: list[str] = Field(
        default=ExclusionPatterns.FILENAME_PATTERNS,
        description="Filename patterns to exclude from scanning",
    )

    # Directory pattern exclusion
    excluded_dir_patterns: list[str] = Field(
        default=ExclusionPatterns.DIRECTORY_PATTERNS,
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

    # Note: File extensions are now managed by FilterConfig.allowed_extensions

    # Batch processing settings
    batch_size: int = Field(
        default=Batch.LARGE_SIZE,
        gt=0,
        description="Number of files to process in each batch",
    )

    # Worker settings
    max_workers: int = Field(
        default=WorkerConfig.DEFAULT,
        gt=0,
        description="Maximum number of worker threads",
    )

    # Timeout settings
    timeout: int = Field(
        default=Timeout.DEFAULT,
        gt=0,
        description="Timeout in seconds for file processing",
    )

    # Parallel scanning settings
    enable_parallel_scanning: bool = Field(
        default=True,
        description="Enable parallel directory scanning",
    )

    parallel_threshold: int = Field(
        default=Batch.PARALLEL_THRESHOLD,
        gt=0,
        description="Minimum file count to use parallel scanning",
    )

    # Filter configuration
    filter_config: FilterConfig = Field(
        default_factory=FilterConfig,
        description="Smart filtering configuration",
        alias="filter",
    )


class AppConfig(BaseModel):
    """Application configuration."""

    name: str = Field(default=Application.NAME, description="Application name")
    version: str = Field(default=Application.VERSION, description="Application version")
    description: str = Field(
        default="Anime Collection Management System",
        description="Application description",
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    theme: str = Field(default="light", description="Application theme (light, dark)")


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Logging level")
    format_string: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
        alias="format",
    )
    file: str = Field(default=Logging.DEFAULT_FILE_PATH, description="Log file path")
    max_bytes: int = Field(
        default=Logging.MAX_BYTES,
        description="Maximum log file size in bytes",  # 10MB
    )
    backup_count: int = Field(
        default=Logging.BACKUP_COUNT,
        description="Number of backup log files to keep",
    )
    console_output: bool = Field(default=True, description="Enable console logging")


class TMDBConfig(BaseModel):
    """TMDB API configuration.

    Note: base_url is managed internally by tmdbv3api library.
    """

    api_key: str = Field(
        default="",
        description="TMDB API key (required for API access)",
    )
    timeout: int = Field(
        default=Timeout.TMDB,
        gt=0,
        description="Request timeout in seconds",
    )
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
    concurrent_requests: int = Field(
        default=APIConfig.DEFAULT_CONCURRENT_REQUESTS,
        gt=0,
        description="Maximum number of concurrent requests",
    )


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = Field(default=True, description="Enable caching")
    ttl: int = Field(
        default=Cache.TTL,
        gt=0,
        description="Cache time-to-live in seconds",
    )
    max_size: int = Field(
        default=Cache.MAX_SIZE,
        gt=0,
        description="Maximum cache size",
    )
    backend: str = Field(
        default=FileSystem.CACHE_BACKEND,
        description="Cache backend (memory, redis, sqlite)",
    )


class PerformanceConfig(BaseModel):
    """Performance configuration."""

    memory_limit: str = Field(
        default=Memory.DEFAULT_LIMIT_STRING,
        description="Memory limit for the application",
    )
    cpu_limit: int = Field(
        default=Memory.DEFAULT_CPU_LIMIT,
        gt=0,
        description="CPU limit for the application",
    )
    enable_profiling: bool = Field(
        default=False,
        description="Enable performance profiling",
    )
    profile_output: str = Field(
        default=Logging.DEFAULT_PROFILING_FILE_PATH,
        description="Profiling output file path",
    )


class FolderSettings(BaseModel):
    """Folder and directory settings (unified from TomlConfig + OrganizationConfig)."""

    source_folder: str = Field(
        default="",
        description="Source folder path for media files to organize",
    )
    target_folder: str = Field(
        default="",
        description="Target folder path for organized media files (required - must be configured)",
    )
    media_type: str = Field(
        default="anime",
        description="Media type for organization (anime, movie, etc.)",
    )
    structure: str = Field(
        default="season_##/korean_title/original_filename",
        description="Directory structure template for organization",
    )
    organize_by_resolution: bool = Field(
        default=False,
        description="Organize files by resolution (e.g., 1080p, 720p)",
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


class SecuritySettings(BaseModel):
    """Security-related settings (from TomlConfig)."""

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


class Settings(BaseSettings):
    """Main settings model containing all configuration sections.

    Unified configuration class that replaces both Settings and TomlConfig.
    Supports loading from TOML files, environment variables, and provides
    strong security validation.
    """

    model_config = SettingsConfigDict(
        # Environment variable configuration
        env_prefix="ANIVAULT_",
        env_nested_delimiter="__",
        env_ignore_empty=True,
        # Ignore unknown fields for backward compatibility
        extra="ignore",
        # Optimize JSON serialization for settings performance
        json_encoders={
            # Custom encoders for specific types if needed
        },
        # Use orjson for better performance in settings serialization
        json_schema_extra={
            "example": {
                "app": {"name": "AniVault", "version": "1.0.0", "debug": False},
                "logging": {"level": "INFO", "format": "json"},
                "tmdb": {
                    "api_key": "your_api_key",  # pragma: allowlist secret
                    # Note: base_url managed by tmdbv3api
                },
                "file_processing": {
                    "max_workers": 4,
                },
                "cache": {"enabled": True, "ttl_seconds": 604800},
                "performance": {"profiling_enabled": False},
            },
        },
    )

    app: AppConfig = Field(default_factory=AppConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    tmdb: TMDBConfig = Field(default_factory=TMDBConfig)
    file_processing: ScanConfig = Field(default_factory=ScanConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)

    # Folder settings (unified from TomlConfig + OrganizationConfig)
    folders: FolderSettings | None = Field(
        default=None,
        description="Folder and directory settings (optional)",
    )
    security: SecuritySettings | None = Field(
        default=None,
        description="Security-related settings (optional)",
    )

    @classmethod
    def from_toml_file(cls, file_path: str | Path) -> Settings:
        """Load settings from a TOML file, with environment variable overrides.

        Environment variables take precedence over TOML values.
        Specifically, if TMDB_API_KEY is set in environment, it will override
        any value (including empty string) in the TOML file.

        Args:
            file_path: Path to the TOML configuration file

        Returns:
            Settings instance loaded from the file

        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            toml.TomlDecodeError: If the TOML file is malformed
            ValidationError: If the configuration doesn't match the schema
        """
        import toml

        file_path = Path(file_path)

        if not file_path.exists():
            msg = f"Configuration file not found: {file_path}"
            raise FileNotFoundError(msg)

        with open(file_path, encoding=Encoding.DEFAULT) as f:
            data = toml.load(f)

        # Override with environment variables (if set)
        # Priority: env vars > TOML file
        env_api_key = os.getenv("TMDB_API_KEY")
        if env_api_key:
            if "tmdb" not in data:
                data["tmdb"] = {}
            data["tmdb"]["api_key"] = env_api_key
            logger.debug("Loaded TMDB API key from environment variable")

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
                    "version": os.getenv("ANIVAULT_VERSION", "0.1.0"),
                    "debug": os.getenv("ANIVAULT_DEBUG", "false").lower() == "true",
                },
                "logging": {
                    "level": os.getenv("ANIVAULT_LOG_LEVEL", "INFO"),
                    "console_output": os.getenv("ANIVAULT_LOG_CONSOLE", "true").lower()
                    == "true",
                },
                "tmdb": {
                    # Note: base_url is managed by tmdbv3api library
                    "api_key": os.getenv("TMDB_API_KEY", ""),
                    "timeout": int(
                        os.getenv("TMDB_TIMEOUT", str(Timeout.TMDB)),
                    ),
                    "retry_attempts": int(
                        os.getenv(
                            "TMDB_RETRY_ATTEMPTS",
                            str(TMDBErrorHandling.RETRY_ATTEMPTS),
                        ),
                    ),
                    "retry_delay": float(
                        os.getenv(
                            "TMDB_RETRY_DELAY",
                            str(TMDBErrorHandling.RETRY_DELAY),
                        ),
                    ),
                    "rate_limit_delay": float(
                        os.getenv(
                            "TMDB_RATE_LIMIT_DELAY",
                            str(TMDBErrorHandling.RATE_LIMIT_DELAY),
                        ),
                    ),
                    "rate_limit_rps": float(
                        os.getenv(
                            "TMDB_RATE_LIMIT_RPS",
                            str(TMDBConstants.RATE_LIMIT_RPS),
                        ),
                    ),
                    "concurrent_requests": int(
                        os.getenv(
                            "TMDB_CONCURRENT_REQUESTS",
                            str(APIConfig.DEFAULT_CONCURRENT_REQUESTS),
                        ),
                    ),
                },
                "file_processing": {
                    "max_workers": int(
                        os.getenv("ANIVAULT_MAX_WORKERS", str(WorkerConfig.DEFAULT)),
                    ),
                    "enable_parallel_scanning": os.getenv(
                        "ANIVAULT_PARALLEL_SCAN",
                        "true",
                    ).lower()
                    == "true",
                    "parallel_threshold": int(
                        os.getenv(
                            "ANIVAULT_PARALLEL_THRESHOLD",
                            str(Batch.PARALLEL_THRESHOLD),
                        ),
                    ),
                },
                "cache": {
                    "enabled": os.getenv(
                        "ANIVAULT_CACHE_ENABLED",
                        "true",
                    ).lower()
                    == "true",
                    "ttl": int(os.getenv("ANIVAULT_CACHE_TTL", str(Cache.TTL))),
                },
            },
        )

    def to_toml_file(self, file_path: str | Path) -> None:
        """Save settings to a TOML file.

        SECURITY: API keys and other secrets are excluded from file output.
        Use environment variables (.env file) to configure sensitive values.

        Args:
            file_path: Path where to save the TOML configuration file
        """
        import toml

        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Exclude sensitive fields (API keys, secrets)
        data = self.model_dump(
            exclude_defaults=False,
            exclude_none=True,
            exclude={"tmdb": {"api_key"}},  # Never save API keys to file
        )

        with open(file_path, "w", encoding=Encoding.DEFAULT) as f:
            toml.dump(data, f)


def _load_env_file() -> None:
    """Load environment variables from .env file.

    This function loads environment variables from a .env file.
    For security reasons, TMDB_API_KEY is required and the function
    will raise an error if the .env file or API key is missing.

    Raises:
        SecurityError: If .env file is missing or TMDB_API_KEY is not configured
        InfrastructureError: If .env file cannot be read due to permission issues
    """
    from anivault.shared.errors import (
        ErrorCode,
        ErrorContext,
        InfrastructureError,
        SecurityError,
    )

    # Check if .env file exists - but allow missing .env if TMDB_API_KEY already set (CI/tests)
    env_file = Path(".env")
    if not env_file.exists():
        # If TMDB_API_KEY is already in environment (CI/tests), allow missing .env
        if "TMDB_API_KEY" in os.environ:
            return

        raise SecurityError(
            code=ErrorCode.MISSING_CONFIG,
            message=(
                "Environment file .env not found. "
                "Copy env.template to .env and configure your TMDB API key."
            ),
            context=ErrorContext(
                operation="load_env",
                additional_data={"file_name": env_file.name},
            ),
        )

    try:
        # Try to use python-dotenv if available
        try:
            import importlib

            dotenv = importlib.import_module("dotenv")
            dotenv.load_dotenv(env_file, override=True)
        except ImportError:
            # Fallback: Load .env file manually
            with open(env_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip("\"'")
                        if key and value and not os.getenv(key):
                            os.environ[key] = value

    except PermissionError as e:
        raise InfrastructureError(
            code=ErrorCode.FILE_PERMISSION_DENIED,
            message=f"Permission denied reading .env file: {env_file}",
            context=ErrorContext(
                operation="load_env",
                additional_data={"file_name": env_file.name},
            ),
            original_error=e,
        ) from e
    except (OSError, ValueError) as e:
        raise InfrastructureError(
            code=ErrorCode.FILE_READ_ERROR,
            message=f"Failed to read .env file: {e}",
            context=ErrorContext(
                operation="load_env",
                additional_data={"file_name": env_file.name},
            ),
            original_error=e,
        ) from e

    # Validate that TMDB_API_KEY is set
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        raise SecurityError(
            code=ErrorCode.MISSING_CONFIG,
            message=(
                "TMDB_API_KEY not found in environment. Set TMDB_API_KEY in .env file."
            ),
            context=ErrorContext(
                operation="validate_api_key",
                additional_data={"env_file_name": env_file.name},
            ),
        )

    # Validate API key format
    api_key = api_key.strip()
    if len(api_key) == 0:
        raise SecurityError(
            code=ErrorCode.INVALID_CONFIG,
            message="TMDB_API_KEY is empty in .env file",
            context=ErrorContext(
                operation="validate_api_key",
                additional_data={"env_file_name": env_file.name},
            ),
        )

    if len(api_key) < 20:
        raise SecurityError(
            code=ErrorCode.INVALID_CONFIG,
            message=(
                f"TMDB_API_KEY appears invalid (too short: {len(api_key)} characters). "
                f"Expected at least 20 characters. Please check your API key."
            ),
            context=ErrorContext(
                operation="validate_api_key",
                additional_data={
                    "env_file_name": env_file.name,
                    "key_length": len(api_key),
                },
            ),
        )


def load_settings(config_path: str | Path | None = None) -> Settings:
    """Load settings from TOML configuration file or environment.

    Args:
        config_path: Optional path to TOML configuration file. If None, tries to load
                    from default locations or environment variables.

    Returns:
        Settings instance loaded from the specified source
    """
    # Load .env file if it exists
    _load_env_file()

    if config_path:
        return Settings.from_toml_file(config_path)

    # Try to load from default configuration file
    default_config_paths = [
        Path("config/config.toml"),
        Path("config.toml"),
        Path.home() / FileSystem.HOME_DIR / "config.toml",
    ]

    for config_path in default_config_paths:
        if config_path.exists():
            return Settings.from_toml_file(config_path)

    # Fall back to environment variables (after .env file has been loaded)
    # Ensure .env file is loaded again before reading environment variables
    _load_env_file()
    return Settings.from_environment()


# Global settings instance (thread-safe)
_settings: Settings | None = None
_settings_lock = threading.RLock()


def get_config() -> Settings:
    """Get the global settings instance (thread-safe).

    Uses double-checked locking pattern to ensure thread-safety
    while minimizing lock overhead.

    Returns:
        The global Settings instance, loading it if necessary.
    """
    global _settings

    # First check (without lock for performance)
    if _settings is None:
        # Second check (with lock for thread-safety)
        with _settings_lock:
            if _settings is None:
                # Load .env file before loading settings
                _load_env_file()
                _settings = load_settings()

    return _settings


def reload_config() -> Settings:
    """Reload the global settings instance from configuration files (thread-safe).

    Forces a reload of the configuration, useful after configuration
    changes are saved to disk.

    Returns:
        The reloaded Settings instance.
    """
    global _settings

    with _settings_lock:
        # Load .env file before loading settings
        _load_env_file()
        _settings = load_settings()

    return _settings


def update_and_save_config(
    updater: typing.Callable[[Settings], None],
    config_path: Path | str = Path("config/config.toml"),
) -> None:
    """Update configuration, validate, save to file, and reload global cache (thread-safe).

    This function provides a safe way to update configuration by:
    1. Creating a deep copy of current settings
    2. Applying the update function
    3. Validating the updated settings
    4. Saving to file if valid
    5. Reloading the global cache

    Args:
        updater: Callable that modifies Settings object in-place
        config_path: Path to save the configuration file

    Raises:
        ApplicationError: If validation fails or save operation fails

    Example:
        >>> def update_tmdb_timeout(cfg: Settings) -> None:
        ...     cfg.tmdb.timeout = 60
        >>> update_and_save_config(update_tmdb_timeout)
    """
    from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext

    global _settings
    config_path = Path(config_path)

    with _settings_lock:
        try:
            # 1. Get current config (will load if needed)
            current = get_config()

            # 2. Create deep copy for validation
            updated = current.model_copy(deep=True)

            # 3. Apply updater function
            updater(updated)

            # 4. Validate updated settings
            updated.model_validate(updated.model_dump())

            # 5. Save to file
            updated.to_toml_file(config_path)

            # 6. Update global cache
            _settings = updated

            logger.info(
                "Configuration updated and saved successfully to %s", config_path
            )

        except Exception as e:
            logger.exception("Failed to update and save configuration")
            raise ApplicationError(
                code=ErrorCode.CONFIGURATION_ERROR,
                message=f"Configuration update failed: {e}",
                context=ErrorContext(
                    operation="update_and_save_config",
                    additional_data={"config_path": str(config_path)},
                ),
                original_error=e,
            ) from e
