"""
Settings Manager for AniVault Configuration

This module provides the SettingsManager class for loading and merging
configuration from multiple sources with proper priority handling:
Environment Variables > TOML File > Default Values
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import toml
from pydantic import ValidationError

from anivault.config.validation import TomlConfig
from anivault.shared.constants import (
    Config,
    Encoding,
)
from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext

logger = logging.getLogger(__name__)


class SettingsManager:
    """Manages hierarchical configuration loading and merging."""

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize the SettingsManager.

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

        # Ensure the configuration directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        logger.debug(
            "SettingsManager initialized with config path: %s",
            self.config_path,
        )

    def _load_toml_config(self) -> dict[str, Any]:
        """Load configuration from TOML file.

        Returns:
            Dictionary containing TOML configuration data

        Raises:
            ConfigurationError: If TOML file is malformed
        """
        try:
            if not self.config_path.exists():
                logger.debug("TOML config file not found: %s", self.config_path)
                return {}

            with open(self.config_path, encoding=Encoding.DEFAULT) as f:
                config_data = toml.load(f)

            logger.debug("Successfully loaded TOML config from: %s", self.config_path)
            return config_data

        except toml.TomlDecodeError as e:
            logger.warning("Malformed TOML file %s: %s", self.config_path, e)
            raise ApplicationError(
                ErrorCode.CONFIG_ERROR,
                f"Malformed TOML configuration file: {self.config_path}",
                ErrorContext(file_path=str(self.config_path)),
            ) from e
        except Exception as e:
            logger.exception("Unexpected error loading TOML config")
            raise ApplicationError(
                ErrorCode.CONFIG_ERROR,
                f"Failed to load TOML configuration: {self.config_path}",
                ErrorContext(file_path=str(self.config_path)),
            ) from e

    @staticmethod
    def _deep_merge_dicts(
        base: dict[str, Any],
        override: dict[str, Any],
    ) -> dict[str, Any]:
        """Deep merge two dictionaries recursively.

        Args:
            base: Base dictionary to merge into
            override: Dictionary with override values

        Returns:
            Merged dictionary with override values taking precedence
        """
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                # Recursively merge nested dictionaries
                result[key] = SettingsManager._deep_merge_dicts(result[key], value)
            else:
                # Override the value
                result[key] = value

        return result

    def _get_merged_config(self) -> dict[str, Any]:
        """Get merged configuration from defaults and TOML file.

        Returns:
            Dictionary containing merged configuration (TOML > Defaults)
        """
        # Get default configuration from Pydantic models
        try:
            default_config = TomlConfig.model_validate({}).model_dump()
        except ValidationError as e:
            logger.exception("Failed to create default configuration")
            raise ApplicationError(
                ErrorCode.CONFIG_ERROR,
                "Failed to create default configuration",
                ErrorContext(operation="get_default_config"),
            ) from e

        # Load TOML configuration
        toml_config = self._load_toml_config()

        # Merge TOML config over defaults (TOML > Defaults)
        merged_config = self._deep_merge_dicts(default_config, toml_config)

        logger.debug("Successfully merged default and TOML configurations")
        return merged_config

    def load_settings(self) -> TomlConfig:
        """Load and validate settings with proper priority.

        Priority: Environment Variables > TOML File > Default Values

        BaseSettings automatically handles environment variables with the following order:
        1. Environment variables (ANIVAULT_APP__NAME, etc.)
        2. Constructor arguments (TOML config)
        3. Default values

        However, constructor arguments take precedence over environment variables.
        To ensure environment variables override TOML values, we:
        1. Create TomlConfig() without arguments (reads environment variables)
        2. Manually apply TOML values only where environment variables don't exist

        Returns:
            Validated TomlConfig object

        Raises:
            ApplicationError: If configuration validation fails or other unexpected error occurs.
        """
        try:
            # Create TomlConfig instance without any arguments
            # This allows BaseSettings to read environment variables first
            settings = TomlConfig()

            # Load TOML configuration
            toml_config = self._load_toml_config()

            # Apply TOML values only where environment variables don't exist
            if toml_config:
                # Check if environment variables exist for each section
                for section_name, section_data in toml_config.items():
                    if not hasattr(settings, section_name):
                        continue

                    section_obj = getattr(settings, section_name)

                    # Apply each field from TOML only if no environment variable exists
                    for field_name, field_value in section_data.items():
                        env_var_name = f"{Config.ENV_PREFIX}{section_name.upper()}{Config.ENV_DELIMITER}{field_name.upper()}"

                        # Only apply TOML value if environment variable doesn't exist
                        if not os.getenv(env_var_name) and hasattr(
                            section_obj,
                            field_name,
                        ):
                            setattr(section_obj, field_name, field_value)

            logger.info("Successfully loaded and validated settings")
            return settings

        except ValidationError as e:
            logger.exception("Configuration validation failed")
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                f"Configuration validation failed: {e}",
                ErrorContext(file_path=str(self.config_path)),
            ) from e
        except Exception as e:
            logger.exception("Unexpected error loading settings")
            raise ApplicationError(
                ErrorCode.CONFIG_ERROR,
                f"Failed to load settings: {e}",
                ErrorContext(file_path=str(self.config_path)),
            ) from e

    def save_default_config(self) -> None:
        """Save default configuration to TOML file.

        This creates a template configuration file that users can modify.
        """
        try:
            # Create default configuration
            default_config = TomlConfig.model_validate({})

            # Convert to dictionary for TOML serialization
            config_dict = default_config.model_dump()

            # Write to TOML file
            with open(self.config_path, "w", encoding=Encoding.DEFAULT) as f:
                toml.dump(config_dict, f)

            logger.info("Default configuration saved to: %s", self.config_path)

        except Exception as e:
            logger.exception("Failed to save default configuration")
            raise ApplicationError(
                ErrorCode.CONFIG_ERROR,
                f"Failed to save default configuration: {e}",
                ErrorContext(file_path=str(self.config_path)),
            ) from e
