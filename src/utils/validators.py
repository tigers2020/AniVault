"""
Configuration validation utilities for AniVault application.

This module provides comprehensive validation functions for configuration values,
including path validation, API key validation, and data type validation.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class ConfigValidator:
    """Comprehensive configuration validator with various validation methods."""

    # Validation patterns
    TMDB_API_KEY_PATTERN = re.compile(r"^[a-f0-9]{32}$", re.IGNORECASE)
    LANGUAGE_CODE_PATTERN = re.compile(r"^[a-z]{2}(-[A-Z]{2})?$")
    THEME_PATTERN = re.compile(r"^(auto|light|dark|system)$")

    # Valid values
    VALID_THEMES = ["auto", "light", "dark", "system"]
    VALID_LANGUAGES = ["ko", "en", "ja", "zh", "ko-KR", "en-US", "ja-JP", "zh-CN"]
    VALID_ORGANIZE_MODES = ["복사", "이동", "copy", "move"]
    VALID_NAMING_SCHEMES = ["standard", "anitopy", "custom"]

    def __init__(self):
        """Initialize the validator."""
        pass

    def validate_api_key(self, api_key: str, api_type: str = "tmdb") -> bool:
        """
        Validate API key format based on type.

        Args:
            api_key: The API key to validate
            api_type: Type of API ('tmdb', 'generic')

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(api_key, str) or not api_key.strip():
            return False

        api_key = api_key.strip()

        if api_type.lower() == "tmdb":
            # TMDB API keys are typically 32 character hexadecimal strings
            return bool(self.TMDB_API_KEY_PATTERN.match(api_key)) and len(api_key) == 32
        elif api_type.lower() == "generic":
            # Generic API key validation (alphanumeric, 16-64 characters)
            return 16 <= len(api_key) <= 64 and api_key.isalnum()
        else:
            # Unknown API type, use generic validation
            return 8 <= len(api_key) <= 128 and api_key.isalnum()

    def validate_path(
        self, path: str, must_exist: bool = False, must_be_directory: bool = False
    ) -> bool:
        """
        Validate file or directory path.

        Args:
            path: The path to validate
            must_exist: Whether the path must exist
            must_be_directory: Whether the path must be a directory

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(path, str) or not path.strip():
            return False

        try:
            path_obj = Path(path.strip())

            # Check if path exists if required
            if must_exist and not path_obj.exists():
                return False

            # Check if it's a directory if required
            if must_be_directory and path_obj.exists() and not path_obj.is_dir():
                return False

            # Check if parent directory exists for new paths
            if not must_exist and not path_obj.parent.exists():
                return False

            # Check for invalid characters (Windows)
            # Note: ':' is valid in drive letters, so we check it more carefully
            invalid_chars = '<>"|?*'
            path_str = str(path_obj)

            # Check for invalid characters, but allow ':' in drive letters
            for char in invalid_chars:
                if char in path_str:
                    return False

            # Check for ':' but allow it only in drive letters (e.g., C:)
            if ":" in path_str:
                # Allow ':' only if it's followed by a backslash (drive letter)
                if not (
                    path_str.count(":") == 1
                    and ":" in path_str
                    and path_str[path_str.find(":") + 1] == "\\"
                ):
                    return False

            return True
        except (OSError, ValueError, TypeError):
            return False

    def validate_theme(self, theme: str) -> bool:
        """
        Validate theme setting.

        Args:
            theme: The theme to validate

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(theme, str):
            return False

        return theme.lower() in self.VALID_THEMES

    def validate_language(self, language: str) -> bool:
        """
        Validate language setting.

        Args:
            language: The language code to validate

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(language, str):
            return False

        return language.lower() in [lang.lower() for lang in self.VALID_LANGUAGES]

    def validate_numeric_range(
        self, value: int | float, min_val: float, max_val: float
    ) -> bool:
        """
        Validate numeric value is within specified range.

        Args:
            value: The numeric value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            True if valid, False otherwise
        """
        # Check if value is actually numeric type
        if not isinstance(value, (int, float)):
            return False

        try:
            numeric_value = float(value)
            return min_val <= numeric_value <= max_val
        except (ValueError, TypeError):
            return False

    def validate_organize_mode(self, mode: str) -> bool:
        """
        Validate file organization mode.

        Args:
            mode: The organization mode to validate

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(mode, str):
            return False

        return mode in self.VALID_ORGANIZE_MODES

    def validate_naming_scheme(self, scheme: str) -> bool:
        """
        Validate naming scheme setting.

        Args:
            scheme: The naming scheme to validate

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(scheme, str):
            return False

        return scheme.lower() in self.VALID_NAMING_SCHEMES

    def validate_boolean(self, value: Any) -> bool:
        """
        Validate boolean value.

        Args:
            value: The value to validate

        Returns:
            True if valid boolean, False otherwise
        """
        return isinstance(value, bool)

    def validate_string_length(
        self, value: str, min_length: int = 0, max_length: int = None
    ) -> bool:
        """
        Validate string length.

        Args:
            value: The string to validate
            min_length: Minimum allowed length
            max_length: Maximum allowed length (None for no limit)

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(value, str):
            return False

        length = len(value)
        if length < min_length:
            return False

        if max_length is not None and length > max_length:
            return False

        return True

    def validate_list_items(self, value: list[Any], item_validator: callable = None) -> bool:
        """
        Validate list and optionally validate each item.

        Args:
            value: The list to validate
            item_validator: Optional function to validate each item

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(value, list):
            return False

        if item_validator is not None:
            return all(item_validator(item) for item in value)

        return True

    def validate_config_section(
        self, config: dict, required_keys: list[str], optional_keys: list[str] = None
    ) -> tuple[bool, list[str]]:
        """
        Validate a configuration section.

        Args:
            config: The configuration section to validate
            required_keys: List of required keys
            optional_keys: List of optional keys

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        if not isinstance(config, dict):
            return False, ["Configuration section must be a dictionary"]

        errors = []

        # Check required keys
        for key in required_keys:
            if key not in config:
                errors.append(f"Missing required key: {key}")

        # Check for unknown keys
        if optional_keys is not None:
            all_valid_keys = set(required_keys + optional_keys)
            for key in config.keys():
                if key not in all_valid_keys:
                    errors.append(f"Unknown key: {key}")

        return len(errors) == 0, errors

    def validate_tmdb_config(self, config: dict) -> tuple[bool, list[str]]:
        """
        Validate TMDB API configuration section.

        Args:
            config: The TMDB configuration to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check API key
        api_key = config.get("api_key")
        if api_key and not self.validate_api_key(api_key, "tmdb"):
            errors.append("Invalid TMDB API key format")

        # Check language
        language = config.get("language", "ko-KR")
        if not self.validate_language(language):
            errors.append(f"Invalid language code: {language}")

        # Check timeout
        timeout = config.get("timeout", 30)
        if not self.validate_numeric_range(timeout, 1, 300):
            errors.append(f"Invalid timeout value: {timeout}")

        # Check retry attempts
        retry_attempts = config.get("retry_attempts", 3)
        if not self.validate_numeric_range(retry_attempts, 0, 10):
            errors.append(f"Invalid retry attempts: {retry_attempts}")

        return len(errors) == 0, errors

    def validate_file_organization_config(self, config: dict) -> tuple[bool, list[str]]:
        """
        Validate file organization configuration section.

        Args:
            config: The file organization configuration to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check destination root
        dest_root = config.get("destination_root", "")
        if dest_root and not self.validate_path(dest_root, must_be_directory=True):
            errors.append(f"Invalid destination root path: {dest_root}")

        # Check organize mode
        organize_mode = config.get("organize_mode", "복사")
        if not self.validate_organize_mode(organize_mode):
            errors.append(f"Invalid organize mode: {organize_mode}")

        # Check naming scheme
        naming_scheme = config.get("naming_scheme", "standard")
        if not self.validate_naming_scheme(naming_scheme):
            errors.append(f"Invalid naming scheme: {naming_scheme}")

        # Check boolean settings
        boolean_settings = [
            "safe_mode",
            "backup_before_organize",
            "prefer_anitopy",
            "realtime_monitoring",
            "show_advanced_options",
        ]
        for setting in boolean_settings:
            value = config.get(setting)
            if value is not None and not self.validate_boolean(value):
                errors.append(f"Invalid boolean value for {setting}: {value}")

        # Check auto refresh interval
        refresh_interval = config.get("auto_refresh_interval", 30)
        if not self.validate_numeric_range(refresh_interval, 1, 3600):
            errors.append(f"Invalid auto refresh interval: {refresh_interval}")

        return len(errors) == 0, errors

    def validate_log_level(self, log_level: str) -> bool:
        """
        Validate log level setting.

        Args:
            log_level: The log level to validate

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(log_level, str):
            return False

        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        return log_level.upper() in valid_levels


# Global validator instance
_validator: ConfigValidator | None = None


def get_validator() -> ConfigValidator:
    """
    Get the global configuration validator instance.

    Returns:
        Global ConfigValidator instance
    """
    global _validator
    if _validator is None:
        _validator = ConfigValidator()
    return _validator
