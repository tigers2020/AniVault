"""Settings loader and singleton manager.

This module handles:
- Environment variable loading from .env files
- Configuration file loading from TOML
- Thread-safe singleton pattern for Settings instance
- Configuration update and save operations

Refactored from monolithic settings.py for better modularity.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from anivault.config.settings import Settings


class SettingsLoader:
    """Thread-safe singleton manager for Settings.

    Uses double-checked locking pattern to ensure thread-safety
    while minimizing lock overhead.
    """

    _instance: Settings | None = None
    _lock: threading.RLock = threading.RLock()

    def get_config(self) -> Settings:
        """Get the global settings instance (thread-safe).

        Uses double-checked locking pattern to ensure thread-safety
        while minimizing lock overhead.

        Returns:
            The global Settings instance, loading it if necessary.
        """
        # First check (without lock for performance)
        if self._instance is None:
            # Second check (with lock for thread-safety)
            with self._lock:
                if self._instance is None:
                    # Load .env file before loading settings
                    _load_env_file()
                    self._instance = load_settings()

        return self._instance

    def reload_config(self) -> Settings:
        """Reload the global settings instance from configuration files.

        Forces a reload of the configuration, useful after configuration
        changes are saved to disk.

        Returns:
            The reloaded Settings instance.
        """
        with self._lock:
            # Load .env file before loading settings
            _load_env_file()
            self._instance = load_settings()

        return self._instance

    def update_and_save_config(
        self,
        updater: Callable[[Settings], None],
        config_path: Path | str = Path("config/config.toml"),
    ) -> None:
        """Update configuration, validate, save to file, and reload global cache.

        This method provides a safe way to update configuration by:
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
        """
        import logging

        from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext

        logger = logging.getLogger(__name__)
        config_path = Path(config_path)

        with self._lock:
            try:
                # 1. Get current config (will load if needed)
                current = self.get_config()

                # 2. Create deep copy for validation
                updated = current.model_copy(deep=True)

                # 3. Apply updater function
                updater(updated)

                # 4. Validate updated settings
                updated.model_validate(updated.model_dump())

                # 5. Save to file
                updated.to_toml_file(config_path)

                # 6. Update global cache
                self._instance = updated

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


def _load_env_file() -> None:
    """Load environment variables from .env file.

    This function loads environment variables from a .env file.
    For security reasons, TMDB_API_KEY is required and the function
    will raise an error if the .env file or API key is missing.

    Raises:
        SecurityError: If .env file is missing or TMDB_API_KEY is not configured
        InfrastructureError: If .env file cannot be read due to permission issues
    """
    import os

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
    # Import Settings at runtime to avoid circular dependency
    from anivault.config.settings import Settings
    from anivault.shared.constants import FileSystem

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
    return Settings()


# Global loader instance
_loader = SettingsLoader()


# Public API (backward compatibility wrappers)
def get_config() -> Settings:
    """Get the global settings instance (thread-safe).

    Returns:
        The global Settings instance, loading it if necessary.
    """
    return _loader.get_config()


def reload_config() -> Settings:
    """Reload the global settings instance from configuration files.

    Returns:
        The reloaded Settings instance.
    """
    return _loader.reload_config()


def update_and_save_config(
    updater: Callable[[Settings], None],
    config_path: Path | str = Path("config/config.toml"),
) -> None:
    """Update configuration, validate, save to file, and reload global cache.

    Args:
        updater: Callable that modifies Settings object in-place
        config_path: Path to save the configuration file
    """
    _loader.update_and_save_config(updater, config_path)


__all__ = [
    "SettingsLoader",
    "get_config",
    "load_settings",
    "reload_config",
    "update_and_save_config",
]
