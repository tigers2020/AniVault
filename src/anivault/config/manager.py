"""
Configuration Manager for AniVault

This module provides the ConfigManager class that orchestrates configuration
loading, validation, and storage with proper separation of concerns.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from anivault.config.loader import ConfigLoader
from anivault.config.storage import ConfigStorage
from anivault.config.validation import TomlConfig
from anivault.config.validator import ConfigValidator
from anivault.shared.constants import Config

logger = logging.getLogger(__name__)


class ConfigManager:
    """Orchestrates configuration loading, validation, and storage."""

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize the ConfigManager.

        Args:
            config_path: Optional path to configuration file. If None, uses
                       default path ~/.anivault/anivault.toml
        """
        if config_path is None:
            self.config_path = (
                Path.home() / Config.DEFAULT_DIR / Config.DEFAULT_FILENAME
            )
        else:
            self.config_path = Path(config_path)

        # Initialize components
        self.loader = ConfigLoader(self.config_path)
        self.storage = ConfigStorage(self.config_path)
        self.validator = ConfigValidator()

    def load_config(self) -> TomlConfig:
        """Load and validate configuration with proper priority.

        Priority: Environment Variables > TOML File > Default Values

        Returns:
            Validated TomlConfig object
        """
        return self.loader.load_validated_config()

    def get_merged_config(self) -> dict[str, Any]:
        """Get merged configuration from defaults and TOML file.

        Returns:
            Dictionary containing merged configuration (TOML > Defaults)
        """
        return self.loader.load_merged_config()

    def save_config(self, config: TomlConfig) -> None:
        """Save configuration to TOML file.

        Args:
            config: TomlConfig object to save

        Raises:
            ValueError: If validation fails
        """
        # Validate before saving
        errors = self.validator.validate_config_object(config)
        if errors:
            error_message = f"Configuration validation failed: {', '.join(errors)}"
            raise ValueError(error_message)

        self.storage.save_config(config)

    def validate_config(self, config_dict: dict[str, Any] | None = None) -> list[str]:
        """Validate configuration dictionary.

        Args:
            config_dict: Configuration dictionary to validate. If None, uses current config.

        Returns:
            List of validation error messages. Empty list if valid.
        """
        if config_dict is None:
            config_dict = self.get_merged_config()

        return self.validator.validate_config_dict(config_dict)

    def save_default_config(self) -> None:
        """Save default configuration to TOML file.

        This creates a template configuration file that users can modify.
        """
        self.storage.save_default_config()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key.

        Args:
            key: Configuration key (supports dot notation for nested keys)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        try:
            config = self.get_merged_config()

            # Support dot notation for nested keys
            keys = key.split(".")
            value = config

            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default

            return value

        except (KeyError, TypeError, AttributeError) as e:
            logger.warning("Failed to get config value for key '%s': %s", key, e)
            return default

    def has(self, key: str) -> bool:
        """Check if configuration key exists.

        Args:
            key: Configuration key (supports dot notation for nested keys)

        Returns:
            True if key exists, False otherwise
        """
        return self.get(key) is not None

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value by key.

        Args:
            key: Configuration key (supports dot notation for nested keys)
            value: Value to set

        Raises:
            ValueError: If validation fails
        """
        # Validate the field value if possible
        keys = key.split(".")
        if len(keys) >= 2:
            section = keys[0]
            field = keys[1]
            errors = self.validator.validate_field_value(section, field, value)
            if errors:
                error_message = f"Validation failed for {key}: {', '.join(errors)}"
                raise ValueError(error_message)

        self.storage.set_nested_value(key, value)

    def rollback_config(self) -> bool:
        """Rollback to backup configuration if available.

        Returns:
            True if rollback was successful, False if no backup available
        """
        return self.storage.rollback_to_backup()

    def cleanup_backup(self) -> None:
        """Remove backup file if it exists."""
        self.storage.cleanup_backup()

    def get_config_schema(self) -> dict[str, Any]:
        """Get the configuration schema.

        Returns:
            JSON schema for the configuration
        """
        return self.validator.get_config_schema()

    def get_field_description(self, section: str, field: str) -> str | None:
        """Get description for a specific configuration field.

        Args:
            section: Configuration section name
            field: Field name within the section

        Returns:
            Field description if found, None otherwise
        """
        return self.validator.get_field_description(section, field)

    def get_required_fields(self, section: str) -> list[str]:
        """Get list of required fields for a configuration section.

        Args:
            section: Configuration section name

        Returns:
            List of required field names
        """
        return self.validator.get_required_fields(section)
