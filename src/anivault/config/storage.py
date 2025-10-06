"""
Configuration Storage for AniVault

This module provides the ConfigStorage class for saving and managing
configuration persistence with backup and rollback capabilities.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

import toml

from anivault.config.validation import TomlConfig
from anivault.shared.constants import Encoding
from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext

logger = logging.getLogger(__name__)


class ConfigStorage:
    """Handles configuration persistence with backup and rollback capabilities."""

    def __init__(self, config_path: Path) -> None:
        """Initialize the ConfigStorage.

        Args:
            config_path: Path to the configuration file
        """
        self.config_path = Path(config_path)
        self.backup_path = self.config_path.with_suffix(".toml.backup")

    def save_config(self, config: TomlConfig) -> None:
        """Save configuration to TOML file with backup.

        Args:
            config: TomlConfig object to save

        Raises:
            ApplicationError: If saving fails
        """
        try:
            # Create backup if file exists
            if self.config_path.exists():
                self._create_backup()

            # Convert to dictionary for TOML serialization
            config_dict = config.model_dump()

            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to TOML file
            with open(self.config_path, "w", encoding=Encoding.DEFAULT) as f:
                toml.dump(config_dict, f)

            logger.info("Configuration saved to: %s", self.config_path)

        except Exception as e:
            logger.exception("Failed to save configuration")
            # Restore backup if save failed
            self._restore_backup()
            raise ApplicationError(
                ErrorCode.CONFIG_ERROR,
                f"Failed to save configuration: {e}",
                ErrorContext(file_path=str(self.config_path)),
            ) from e

    def save_config_dict(self, config_dict: dict[str, Any]) -> None:
        """Save configuration dictionary to TOML file.

        Args:
            config_dict: Configuration dictionary to save

        Raises:
            ApplicationError: If saving fails
        """
        try:
            # Create backup if file exists
            if self.config_path.exists():
                self._create_backup()

            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to TOML file
            with open(self.config_path, "w", encoding=Encoding.DEFAULT) as f:
                toml.dump(config_dict, f)

            logger.info("Configuration dictionary saved to: %s", self.config_path)

        except Exception as e:
            logger.exception("Failed to save configuration dictionary")
            # Restore backup if save failed
            self._restore_backup()
            raise ApplicationError(
                ErrorCode.CONFIG_ERROR,
                f"Failed to save configuration dictionary: {e}",
                ErrorContext(file_path=str(self.config_path)),
            ) from e

    def save_default_config(self) -> None:
        """Save default configuration to TOML file.

        This creates a template configuration file that users can modify.
        """
        try:
            # Create default configuration
            default_config = TomlConfig.model_validate({})

            # Save it
            self.save_config(default_config)

            logger.info("Default configuration saved to: %s", self.config_path)

        except Exception as e:
            logger.exception("Failed to save default configuration")
            raise ApplicationError(
                ErrorCode.CONFIG_ERROR,
                f"Failed to save default configuration: {e}",
                ErrorContext(file_path=str(self.config_path)),
            ) from e

    def set_nested_value(self, key: str, value: Any) -> None:
        """Set a configuration value by key with dot notation support.

        Args:
            key: Configuration key (supports dot notation for nested keys)
            value: Value to set

        Raises:
            ApplicationError: If setting fails
        """
        try:
            # Load existing TOML config
            from anivault.config.loader import ConfigLoader
            loader = ConfigLoader(self.config_path)
            toml_config = loader.load_toml_config()

            # Support dot notation for nested keys
            keys = key.split(".")
            current = toml_config

            # Navigate to the parent of the target key
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]

            # Set the value
            current[keys[-1]] = value

            # Save back to TOML file
            self.save_config_dict(toml_config)

            logger.debug("Set config value: %s = %s", key, value)

        except Exception as e:
            logger.exception("Failed to set config value for key '%s'", key)
            raise ApplicationError(
                ErrorCode.CONFIG_ERROR,
                f"Failed to set config value for key '{key}': {e}",
                ErrorContext(file_path=str(self.config_path)),
            ) from e

    def _create_backup(self) -> None:
        """Create a backup of the current configuration file."""
        try:
            if self.config_path.exists():
                shutil.copy2(self.config_path, self.backup_path)
                logger.debug("Created backup: %s", self.backup_path)
        except (OSError, PermissionError, FileNotFoundError) as e:
            logger.warning("Failed to create backup: %s", e)

    def _restore_backup(self) -> None:
        """Restore configuration from backup if available."""
        try:
            if self.backup_path.exists():
                shutil.copy2(self.backup_path, self.config_path)
                logger.info("Restored configuration from backup")
        except (OSError, PermissionError, FileNotFoundError) as e:
            logger.warning("Failed to restore backup: %s", e)

    def rollback_to_backup(self) -> bool:
        """Rollback to backup configuration if available.

        Returns:
            True if rollback was successful, False if no backup available
        """
        try:
            if self.backup_path.exists():
                self._restore_backup()
                logger.info("Successfully rolled back to backup configuration")
                return True
            logger.warning("No backup available for rollback")
            return False
        except (OSError, PermissionError, FileNotFoundError):
            logger.exception("Failed to rollback configuration")
            return False

    def cleanup_backup(self) -> None:
        """Remove backup file if it exists."""
        try:
            if self.backup_path.exists():
                self.backup_path.unlink()
                logger.debug("Cleaned up backup file")
        except (OSError, PermissionError) as e:
            logger.warning("Failed to cleanup backup: %s", e)
