"""
CLI Utilities for Configuration Integration

This module provides utilities for integrating configuration management
with the CLI system, allowing dynamic default values from configuration files.
"""

import argparse
import logging
from pathlib import Path
from typing import Any, Optional

from anivault.config import ConfigManager

logger = logging.getLogger(__name__)


class ConfigAwareArgumentParser(argparse.ArgumentParser):
    """
    An argument parser that can load default values from configuration files.

    This parser extends argparse.ArgumentParser to automatically load
    configuration values and use them as defaults for CLI arguments.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the parser with configuration support."""
        super().__init__(*args, **kwargs)
        self._config_manager: Optional[ConfigManager] = None
        self._config_loaded = False

    def load_config(self, config_path: Optional[Path] = None) -> None:
        """
        Load configuration from file.

        Args:
            config_path: Optional path to configuration file.
                        If None, uses default configuration path.
        """
        try:
            self._config_manager = ConfigManager(config_path)
            # Check if config file exists before trying to load
            if config_path and not config_path.exists():
                logger.warning(f"Configuration file not found: {config_path}")
                self._config_loaded = False
                return

            self._config_manager.load_config()
            self._config_loaded = True
            logger.debug("Configuration loaded successfully for CLI defaults")
        except Exception as e:
            logger.warning(f"Failed to load configuration for CLI defaults: {e}")
            self._config_loaded = False

    def add_argument_with_config_default(
        self,
        *args,
        config_key: Optional[str] = None,
        config_section: Optional[str] = None,
        **kwargs,
    ) -> argparse.Action:
        """
        Add an argument with configuration-based default value.

        Args:
            *args: Standard argparse argument specification
            config_key: Key in the configuration to use as default
            config_section: Section in the configuration (e.g., 'tmdb', 'app')
            **kwargs: Standard argparse argument options

        Returns:
            The created argument action
        """
        # Get default value from configuration if available
        if self._config_loaded and config_key and config_section:
            try:
                config_value = self._get_config_value(config_section, config_key)
                if config_value is not None:
                    kwargs["default"] = config_value
                    logger.debug(
                        f"Using config default for {config_key}: {config_value}"
                    )
            except Exception as e:
                logger.warning(f"Failed to get config value for {config_key}: {e}")

        return self.add_argument(*args, **kwargs)

    def _get_config_value(self, section: str, key: str) -> Any:
        """
        Get a value from the loaded configuration.

        Args:
            section: Configuration section name
            key: Configuration key name

        Returns:
            Configuration value or None if not found
        """
        if not self._config_manager or not self._config_loaded:
            return None

        try:
            config = self._config_manager.get_merged_config()
            if section in config and key in config[section]:
                return config[section][key]
        except Exception as e:
            logger.warning(f"Failed to access config section {section}, key {key}: {e}")

        return None


def create_config_aware_parser(
    description: str,
    config_path: Optional[Path] = None,
    **kwargs,
) -> ConfigAwareArgumentParser:
    """
    Create a configuration-aware argument parser.

    Args:
        description: Parser description
        config_path: Optional path to configuration file
        **kwargs: Additional parser arguments

    Returns:
        Configured ConfigAwareArgumentParser instance
    """
    parser = ConfigAwareArgumentParser(description=description, **kwargs)
    if config_path:
        parser.load_config(config_path)
    return parser


def apply_config_defaults(
    args: argparse.Namespace,
    config_manager: ConfigManager,
    config_mappings: dict[str, dict[str, str]],
) -> None:
    """
    Apply configuration defaults to parsed arguments.

    This function can be used as a post-processing step to apply
    configuration values to arguments that weren't explicitly set.

    Args:
        args: Parsed arguments namespace
        config_manager: Configuration manager instance
        config_mappings: Dictionary mapping argument names to config sections/keys
                        Format: {arg_name: {section: 'section_name', key: 'key_name'}}
    """
    try:
        config = config_manager.get_merged_config()

        for arg_name, mapping in config_mappings.items():
            section = mapping.get("section")
            key = mapping.get("key")

            if not section or not key:
                continue

            # Check if argument was explicitly set (not using default)
            if hasattr(args, arg_name):
                current_value = getattr(args, arg_name)

                # If value is None or matches the default, try to get from config
                if current_value is None or current_value == argparse.SUPPRESS:
                    try:
                        if section in config and key in config[section]:
                            config_value = config[section][key]
                            setattr(args, arg_name, config_value)
                            logger.debug(
                                f"Applied config default for {arg_name}: {config_value}"
                            )
                    except Exception as e:
                        logger.warning(
                            f"Failed to apply config default for {arg_name}: {e}"
                        )

    except Exception as e:
        logger.warning(f"Failed to apply configuration defaults: {e}")


def get_config_value(
    config_manager: ConfigManager,
    section: str,
    key: str,
    default: Any = None,
) -> Any:
    """
    Get a configuration value with fallback to default.

    Args:
        config_manager: Configuration manager instance
        section: Configuration section name
        key: Configuration key name
        default: Default value if configuration value not found

    Returns:
        Configuration value or default
    """
    try:
        # Check if config file exists
        if (
            hasattr(config_manager, "config_path")
            and config_manager.config_path
            and not config_manager.config_path.exists()
        ):
            return default

        config = config_manager.get_merged_config()
        if section in config and key in config[section]:
            return config[section][key]
    except Exception as e:
        logger.warning(f"Failed to get config value for {section}.{key}: {e}")

    return default


def create_config_mappings() -> dict[str, dict[str, str]]:
    """
    Create standard configuration mappings for common CLI arguments.

    Returns:
        Dictionary mapping argument names to configuration sections/keys
    """
    return {
        "workers": {"section": "performance", "key": "max_workers"},
        "rate_limit": {"section": "tmdb", "key": "rate_limit_delay"},
        "concurrent": {"section": "tmdb", "key": "retry_attempts"},
        "extensions": {"section": "file_processing", "key": "supported_extensions"},
        "cache_dir": {"section": "cache", "key": "backend"},
        "log_level": {"section": "logging", "key": "level"},
        "verbose": {"section": "app", "key": "debug"},
    }
