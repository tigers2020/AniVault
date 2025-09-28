"""Configuration management for AniVault.

This module handles loading configuration from pyproject.toml and provides
default values for all application settings.
"""

import sys
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib


class Config:
    """Application configuration container."""

    def __init__(self, config_dict: dict[str, Any]) -> None:
        """Initialize configuration from dictionary.

        Args:
            config_dict: Configuration dictionary from TOML file.
        """
        self.log_file = config_dict.get("log_file", "logs/anivault.log")
        self.log_level = config_dict.get("log_level", "INFO")
        self.log_max_bytes = config_dict.get("log_max_bytes", 10485760)  # 10MB
        self.log_backup_count = config_dict.get("log_backup_count", 5)
        self.media_extensions = config_dict.get(
            "media_extensions", [".mkv", ".mp4", ".avi"]
        )

    def get_log_file_path(self) -> Path:
        """Get the absolute path to the log file.

        Returns:
            Path object for the log file.
        """
        log_path = Path(self.log_file)
        if not log_path.is_absolute():
            # Make relative to project root
            project_root = self._find_project_root()
            log_path = project_root / log_path
        return log_path

    def _find_project_root(self) -> Path:
        """Find the project root directory.

        Returns:
            Path to the project root directory.
        """
        current = Path(__file__).parent
        while current != current.parent:
            if (current / "pyproject.toml").exists():
                return current
            current = current.parent
        # Fallback to current working directory
        return Path.cwd()


def load_config(config_path: Path | None = None) -> Config:
    """Load configuration from pyproject.toml or custom config file.

    Args:
        config_path: Optional path to custom configuration file.

    Returns:
        Config object with loaded settings.
    """
    if config_path and config_path.exists():
        # Load from custom config file
        try:
            with config_path.open("rb") as f:
                data = tomllib.load(f)
            return Config(data)
        except Exception:
            # Fall back to default if custom config fails
            pass

    # Load from pyproject.toml
    project_root = _find_project_root()
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        # Return default configuration if pyproject.toml not found
        return Config({})

    try:
        with pyproject_path.open("rb") as f:
            data = tomllib.load(f)

        # Extract anivault config section
        anivault_config = data.get("tool", {}).get("anivault", {}).get("config", {})
        return Config(anivault_config)

    except (OSError, ValueError, KeyError) as e:
        # Log the error and return default config
        print(f"Warning: Failed to load configuration: {e}", file=sys.stderr)
        return Config({})


def _find_project_root() -> Path:
    """Find the project root directory.

    Returns:
        Path to the project root directory.
    """
    current = Path(__file__).parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    # Fallback to current working directory
    return Path.cwd()


# Global configuration instance
APP_CONFIG = load_config()
