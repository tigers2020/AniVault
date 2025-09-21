"""Enhanced configuration management for AniVault application.

This module provides a comprehensive configuration system with security features,
validation, and thread-safe access for managing application settings.
"""

from __future__ import annotations

import base64
import logging
import threading
from pathlib import Path
from typing import Any

from .config_manager import ConfigManager
from .config_schema import get_schema_validator
from .secure_storage import get_secure_storage

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validates configuration values and structure."""

    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """Validate TMDB API key format."""
        # TMDB API keys are typically 32 characters long
        return len(api_key) >= 20 and api_key.isalnum()

    @staticmethod
    def validate_path(path: str) -> bool:
        """Validate if path exists and is accessible."""
        if not isinstance(path, str) or not path.strip():
            return False
        try:
            path_obj = Path(path)
            return path_obj.exists() or path_obj.parent.exists()
        except (OSError, ValueError):
            return False

    @staticmethod
    def validate_theme(theme: str) -> bool:
        """Validate theme setting."""
        valid_themes = ["auto", "light", "dark", "system"]
        return theme in valid_themes

    @staticmethod
    def validate_language(language: str) -> bool:
        """Validate language setting."""
        valid_languages = ["ko", "en", "ja", "zh"]
        return language in valid_languages

    @staticmethod
    def validate_numeric_range(value: int | float, min_val: float, max_val: float) -> bool:
        """Validate numeric value is within range."""
        return min_val <= value <= max_val


class SecureConfigManager:
    """Enhanced configuration manager with security features and thread safety.

    This class wraps the base ConfigManager and adds:
    - Base64 encoding for sensitive data
    - Thread-safe access
    - Enhanced validation
    - Automatic encryption/decryption
    """

    def __init__(self, config_path: Path | None = None):
        """Initialize the secure configuration manager.

        Args:
            config_path: Path to the configuration file. If None, uses default location.
        """
        self._base_manager = ConfigManager(config_path)
        self._lock = threading.RLock()
        self._validator = ConfigValidator()
        self._schema_validator = get_schema_validator()
        self._secure_storage = get_secure_storage()

        # Keys that should be encrypted
        self._encrypted_keys = [
            "services.tmdb_api.api_key",
            "services.api_keys.tmdb",
            "user_preferences.gui_state.last_source_directory",
            "user_preferences.gui_state.last_destination_directory",
            "application.file_organization.destination_root",
        ]

        # Initialize security settings if not present
        self._ensure_security_settings()

    def _ensure_security_settings(self) -> None:
        """Ensure security settings are present in configuration."""
        with self._lock:
            if not self._base_manager.get("security"):
                self._base_manager.set(
                    "security", {"encryption_enabled": True, "encrypted_keys": self._encrypted_keys}
                )
                self._base_manager.save_config()

    def _encode_sensitive_data(self, data: str) -> str:
        """Encode sensitive data using secure storage."""
        if not data:
            return data
        try:
            return self._secure_storage.encrypt_data(data)
        except Exception as e:
            logger.error("Failed to encode sensitive data: %s", str(e))
            # Fallback to base64
            try:
                encoded_bytes = base64.b64encode(data.encode("utf-8"))
                return encoded_bytes.decode("utf-8")
            except Exception:
                return data

    def _decode_sensitive_data(self, encoded_data: str) -> str:
        """Decode sensitive data using secure storage."""
        if not encoded_data:
            return encoded_data
        try:
            return self._secure_storage.decrypt_data(encoded_data)
        except Exception as e:
            logger.error("Failed to decode sensitive data: %s", str(e))
            # Fallback to base64
            try:
                decoded_bytes = base64.b64decode(encoded_data.encode("utf-8"))
                return decoded_bytes.decode("utf-8")
            except Exception:
                return encoded_data

    def _is_sensitive_key(self, key_path: str) -> bool:
        """Check if a key path contains sensitive data."""
        return any(encrypted_key in key_path for encrypted_key in self._encrypted_keys)

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a configuration value with automatic decryption.

        Args:
            key_path: Dot-separated path to the configuration key
            default: Default value if key is not found

        Returns:
            Configuration value or default
        """
        with self._lock:
            # Try to get the value directly first
            value = self._base_manager.get(key_path, default)

            # If it's a sensitive key or if direct value is default, try to get encrypted version
            if (self._is_sensitive_key(key_path) or value == default) and value == default:
                encrypted_key = f"{key_path}_encrypted"
                encrypted_value = self._base_manager.get(encrypted_key)
                if encrypted_value:
                    value = self._decode_sensitive_data(encrypted_value)

            return value

    def set(self, key_path: str, value: Any, encrypt: bool | None = None) -> None:
        """Set a configuration value with optional encryption.

        Args:
            key_path: Dot-separated path to the configuration key
            value: Value to set
            encrypt: Whether to encrypt the value. If None, auto-detect based on key type.
        """
        with self._lock:
            # Check if encryption is globally disabled
            encryption_enabled = self._base_manager.get("security.encryption_enabled", True)

            # Auto-detect if encryption is needed
            if encrypt is None:
                encrypt = (
                    self._is_sensitive_key(key_path)
                    and isinstance(value, str)
                    and encryption_enabled
                )

            if encrypt and isinstance(value, str) and encryption_enabled:
                # Store encrypted version
                encrypted_value = self._encode_sensitive_data(value)
                encrypted_key = f"{key_path}_encrypted"
                self._base_manager.set(encrypted_key, encrypted_value)
                logger.debug("Encrypted value stored for key: %s", key_path)
            else:
                # Store normal value
                self._base_manager.set(key_path, value)
                logger.debug("Configuration set: %s = %s", key_path, value)

    def get_tmdb_api_key(self) -> str | None:
        """Get TMDB API key with automatic decryption."""
        result = self.get("services.tmdb_api.api_key") or self.get("services.api_keys.tmdb")
        return result if isinstance(result, str) else None

    def set_tmdb_api_key(self, api_key: str) -> bool:
        """Set TMDB API key with validation and encryption.

        Args:
            api_key: The API key to set

        Returns:
            True if set successfully, False if validation failed
        """
        if not self._validator.validate_api_key(api_key):
            logger.error("Invalid TMDB API key format")
            return False

        self.set("services.tmdb_api.api_key", api_key, encrypt=True)
        return True

    def get_destination_root(self) -> str:
        """Get destination root directory with validation."""
        path = self.get("application.file_organization.destination_root", "")
        if isinstance(path, str) and path and not self._validator.validate_path(path):
            logger.warning("Destination root path is not accessible: %s", path)
        return str(path) if path else ""

    def set_destination_root(self, path: str) -> bool:
        """Set destination root directory with validation.

        Args:
            path: The destination path to set

        Returns:
            True if set successfully, False if validation failed
        """
        if not self._validator.validate_path(path):
            logger.error("Invalid destination root path: %s", path)
            return False

        self.set("application.file_organization.destination_root", path, encrypt=True)
        return True

    def get_theme(self) -> str:
        """Get current theme with validation."""
        theme = self.get("user_preferences.theme_preferences.theme", "auto")
        if not isinstance(theme, str) or not self._validator.validate_theme(theme):
            logger.warning("Invalid theme setting, using default: %s", theme)
            return "auto"
        return theme

    def set_theme(self, theme: str) -> bool:
        """Set current theme with validation.

        Args:
            theme: The theme to set

        Returns:
            True if set successfully, False if validation failed
        """
        if not self._validator.validate_theme(theme):
            logger.error("Invalid theme: %s", theme)
            return False

        self.set("user_preferences.theme_preferences.theme", theme)
        return True

    def get_language(self) -> str:
        """Get current language with validation."""
        language = self.get("user_preferences.theme_preferences.language", "ko")
        if not isinstance(language, str) or not self._validator.validate_language(language):
            logger.warning("Invalid language setting, using default: %s", language)
            return "ko"
        return language

    def set_language(self, language: str) -> bool:
        """Set current language with validation.

        Args:
            language: The language to set

        Returns:
            True if set successfully, False if validation failed
        """
        if not self._validator.validate_language(language):
            logger.error("Invalid language: %s", language)
            return False

        self.set("user_preferences.theme_preferences.language", language)
        return True

    def save_config(self) -> bool:
        """Save configuration to file with thread safety."""
        with self._lock:
            return self._base_manager.save_config()

    def reload_config(self) -> None:
        """Reload configuration from file with thread safety."""
        with self._lock:
            self._base_manager.reload_config()

    def validate_config(self) -> bool:
        """Validate the current configuration with enhanced checks.

        Returns:
            True if configuration is valid, False otherwise
        """
        with self._lock:
            try:
                # Get current configuration
                config = self._base_manager.get_all_config()

                # Use schema validator for comprehensive validation
                is_valid, errors = self._schema_validator.validate_config(config)

                if not is_valid:
                    for error in errors:
                        logger.error("Configuration validation error: %s", error)
                    return False

                # Additional runtime validation
                api_key = self.get_tmdb_api_key()
                if api_key and not self._validator.validate_api_key(api_key):
                    logger.error("Invalid TMDB API key format")
                    return False

                # Validate paths
                dest_root = self.get_destination_root()
                if dest_root and not self._validator.validate_path(dest_root):
                    logger.warning("Destination root path is not accessible")

                return True
            except Exception as e:
                logger.error("Configuration validation failed: %s", str(e))
                return False

    def get_validation_errors(self) -> list[str]:
        """Get detailed validation errors for the current configuration.

        Returns:
            List of validation error messages
        """
        with self._lock:
            try:
                config = self._base_manager.get_all_config()
                return self._schema_validator.get_schema_errors(config)
            except Exception as e:
                logger.error("Failed to get validation errors: %s", str(e))
                return [f"Error retrieving validation errors: {e!s}"]

    def get_all_config(self) -> dict[str, Any]:
        """Get the entire configuration dictionary (sensitive data will be decrypted)."""
        with self._lock:
            config = self._base_manager.get_all_config()

            # Decrypt sensitive values in the returned config
            def decrypt_sensitive_values(obj: Any, path: str = "") -> None:
                if isinstance(obj, dict):
                    # Create a list of keys to avoid modification during iteration
                    keys_to_process = list(obj.keys())
                    keys_to_remove = []

                    for key in keys_to_process:
                        value = obj[key]
                        current_path = f"{path}.{key}" if path else key

                        # Check if this is an encrypted key (ends with _encrypted)
                        if key.endswith("_encrypted") and isinstance(value, str):
                            # Get the original key name
                            original_key = key[:-10]  # Remove "_encrypted" suffix
                            original_path = f"{path}.{original_key}" if path else original_key

                            # If this is a sensitive key, decrypt it
                            if self._is_sensitive_key(original_path):
                                try:
                                    decoded = self._decode_sensitive_data(value)
                                    if decoded != value:  # Only replace if decoding was successful
                                        # Replace the encrypted key with the decrypted value
                                        obj[original_key] = decoded
                                        # Mark the encrypted key for removal
                                        keys_to_remove.append(key)
                                except Exception:
                                    pass  # Keep original value if decoding fails
                        elif isinstance(value, str) and self._is_sensitive_key(current_path):
                            # Try to decrypt if it looks like base64
                            try:
                                decoded = self._decode_sensitive_data(value)
                                if decoded != value:  # Only replace if decoding was successful
                                    obj[key] = decoded
                            except Exception:
                                pass  # Keep original value if decoding fails
                        elif isinstance(value, dict):
                            decrypt_sensitive_values(value, current_path)

                    # Remove encrypted keys after iteration
                    for key in keys_to_remove:
                        obj.pop(key, None)

            decrypt_sensitive_values(config)
            return config

    def backup_config(self, backup_path: Path | None = None) -> bool:
        """Create a backup of the current configuration with thread safety."""
        with self._lock:
            return self._base_manager.backup_config(backup_path)

    def rotate_encryption_key(self) -> bool:
        """Rotate the encryption key for enhanced security.

        Returns:
            True if key rotation was successful, False otherwise
        """
        with self._lock:
            try:
                # Get all current sensitive values
                sensitive_values = {}
                for key_path in self._encrypted_keys:
                    value = self.get(key_path)
                    if value:
                        sensitive_values[key_path] = value

                # Rotate the encryption key
                success = self._secure_storage.rotate_encryption_key()
                if not success:
                    return False

                # Re-encrypt all sensitive values with new key
                for key_path, value in sensitive_values.items():
                    self.set(key_path, value, encrypt=True)

                # Save the updated configuration
                return self.save_config()

            except Exception as e:
                logger.error("Failed to rotate encryption key: %s", str(e))
                return False

    def get_security_status(self) -> dict[str, Any]:
        """Get security status information.

        Returns:
            Dictionary containing security status information
        """
        with self._lock:
            return {
                "encryption_enabled": self._base_manager.get("security.encryption_enabled", True),
                "encrypted_keys_count": len(self._encrypted_keys),
                "secure_storage_available": self._secure_storage is not None,
                "key_file_exists": (
                    self._secure_storage.key_manager.key_file_path.exists()
                    if self._secure_storage
                    else False
                ),
            }


# Global secure configuration manager instance
_secure_config_manager: SecureConfigManager | None = None


def get_secure_config_manager() -> SecureConfigManager:
    """Get the global secure configuration manager instance.

    Returns:
        Global SecureConfigManager instance
    """
    global _secure_config_manager
    if _secure_config_manager is None:
        _secure_config_manager = SecureConfigManager()
    return _secure_config_manager


def initialize_secure_config(config_path: Path | None = None) -> SecureConfigManager:
    """Initialize the global secure configuration manager.

    Args:
        config_path: Path to configuration file

    Returns:
        Initialized SecureConfigManager instance
    """
    global _secure_config_manager
    _secure_config_manager = SecureConfigManager(config_path)
    return _secure_config_manager
