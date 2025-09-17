"""
Configuration management for AniVault application.

This module provides centralized configuration management for the application,
including API keys, user preferences, and application settings.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Manages application configuration including API keys, settings, and user preferences.

    This class provides a centralized way to access and modify configuration
    settings throughout the application.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the configuration manager.

        Args:
            config_path: Path to the configuration file. If None, uses default location.
        """
        if config_path is None:
            # Default config path in data directory
            self.config_path = Path("data/config/unified_config.json")
        else:
            self.config_path = Path(config_path)

        self._config: dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, encoding="utf-8") as f:
                    self._config = json.load(f)
                logger.info("Configuration loaded from: %s", self.config_path)
            else:
                logger.warning("Configuration file not found: %s", self.config_path)
                self._config = self._get_default_config()
        except Exception as e:
            logger.error("Failed to load configuration: %s", str(e))
            self._config = self._get_default_config()

    def _get_default_config(self) -> dict[str, Any]:
        """Get default configuration."""
        return {
            "version": "1.0.0",
            "services": {"mcp_server": {}, "tmdb_api": {}, "api_keys": {}},
            "application": {
                "file_organization": {
                    "destination_root": "",
                    "organize_mode": "복사",
                    "naming_scheme": "standard",
                    "safe_mode": True,
                    "backup_before_organize": False,
                    "prefer_anitopy": False,
                    "fallback_parser": "FileParser",
                    "realtime_monitoring": False,
                    "auto_refresh_interval": 30,
                    "show_advanced_options": False,
                },
                "backup_settings": {"backup_location": "", "max_backup_count": 10},
                "logging_config": {"log_level": "INFO", "log_to_file": False},
                "performance_settings": {},
            },
            "user_preferences": {
                "gui_state": {
                    "window_geometry": None,
                    "last_source_directory": "",
                    "last_destination_directory": "",
                    "remember_last_session": True,
                },
                "accessibility": {
                    "high_contrast_mode": False,
                    "keyboard_navigation": True,
                    "screen_reader_support": True,
                },
                "theme_preferences": {"theme": "auto", "language": "ko"},
                "language_settings": {},
            },
            "metadata": {"migrated_at": "", "migration_version": "1.0.0", "source_files": []},
        }

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.

        Args:
            key_path: Dot-separated path to the configuration key (e.g., 'services.tmdb_api.api_key')
            default: Default value if key is not found

        Returns:
            Configuration value or default
        """
        keys = key_path.split(".")
        value = self._config

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key_path: str, value: Any) -> None:
        """
        Set a configuration value using dot notation.

        Args:
            key_path: Dot-separated path to the configuration key
            value: Value to set
        """
        keys = key_path.split(".")
        config = self._config

        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        # Set the final value
        config[keys[-1]] = value
        logger.debug("Configuration set: %s = %s", key_path, value)

    def get_tmdb_api_key(self) -> Optional[str]:
        """Get TMDB API key."""
        return self.get("services.tmdb_api.api_key") or self.get("services.api_keys.tmdb")

    def get_tmdb_language(self) -> str:
        """Get TMDB language setting."""
        return self.get("services.tmdb_api.language", "ko-KR")

    def get_destination_root(self) -> str:
        """Get destination root directory."""
        return self.get("application.file_organization.destination_root", "")

    def set_destination_root(self, path: str) -> None:
        """Set destination root directory."""
        self.set("application.file_organization.destination_root", path)

    def get_last_source_directory(self) -> str:
        """Get last used source directory."""
        return self.get("user_preferences.gui_state.last_source_directory", "")

    def set_last_source_directory(self, path: str) -> None:
        """Set last used source directory."""
        self.set("user_preferences.gui_state.last_source_directory", path)

    def get_last_destination_directory(self) -> str:
        """Get last used destination directory."""
        return self.get("user_preferences.gui_state.last_destination_directory", "")

    def set_last_destination_directory(self, path: str) -> None:
        """Set last used destination directory."""
        self.set("user_preferences.gui_state.last_destination_directory", path)

    def get_theme(self) -> str:
        """Get current theme."""
        return self.get("user_preferences.theme_preferences.theme", "auto")

    def set_theme(self, theme: str) -> None:
        """Set current theme."""
        self.set("user_preferences.theme_preferences.theme", theme)

    def get_language(self) -> str:
        """Get current language."""
        return self.get("user_preferences.theme_preferences.language", "ko")

    def set_language(self, language: str) -> None:
        """Set current language."""
        self.set("user_preferences.theme_preferences.language", language)

    def save_config(self) -> bool:
        """
        Save configuration to file.

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)

            logger.info("Configuration saved to: %s", self.config_path)
            return True
        except Exception as e:
            logger.error("Failed to save configuration: %s", str(e))
            return False

    def reload_config(self) -> None:
        """Reload configuration from file."""
        self._load_config()

    def get_all_config(self) -> dict[str, Any]:
        """Get the entire configuration dictionary."""
        return self._config.copy()

    def validate_config(self) -> bool:
        """
        Validate the current configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            # Check required fields
            required_paths = ["version", "services", "application", "user_preferences"]

            for path in required_paths:
                if self.get(path) is None:
                    logger.error("Missing required configuration section: %s", path)
                    return False

            # Validate TMDB API key if present
            api_key = self.get_tmdb_api_key()
            if api_key and not isinstance(api_key, str):
                logger.error("TMDB API key must be a string")
                return False

            # Basic validation for other settings
            theme = self.get_theme()
            if theme not in ["auto", "light", "dark", "system"]:
                logger.warning("Invalid theme setting: %s", theme)

            language = self.get_language()
            if language not in ["ko", "en", "ja", "zh"]:
                logger.warning("Invalid language setting: %s", language)

            return True
        except Exception as e:
            logger.error("Configuration validation failed: %s", str(e))
            return False

    def backup_config(self, backup_path: Optional[Path] = None) -> bool:
        """
        Create a backup of the current configuration.

        Args:
            backup_path: Path for backup file. If None, creates timestamped backup.

        Returns:
            True if backup created successfully, False otherwise
        """
        try:
            if backup_path is None:
                from datetime import datetime

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.config_path.parent / f"unified_config_backup_{timestamp}.json"

            backup_path = Path(backup_path)
            backup_path.parent.mkdir(parents=True, exist_ok=True)

            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)

            logger.info("Configuration backup created: %s", backup_path)
            return True
        except Exception as e:
            logger.error("Failed to create configuration backup: %s", str(e))
            return False


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """
    Get the global configuration manager instance.

    Returns:
        Global ConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def initialize_config(config_path: Optional[Path] = None) -> ConfigManager:
    """
    Initialize the global configuration manager.

    Args:
        config_path: Path to configuration file

    Returns:
        Initialized ConfigManager instance
    """
    global _config_manager
    _config_manager = ConfigManager(config_path)
    return _config_manager
