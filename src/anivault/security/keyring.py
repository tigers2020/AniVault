"""
Secure Keyring System for AniVault.

This module provides a secure keyring system for storing and retrieving
encrypted API keys and other sensitive data using PIN-based encryption.
"""
from __future__ import annotations

import os
from pathlib import Path

from anivault.security.encryption import DecryptionError, EncryptionService
from anivault.shared.constants.system import FileSystem
from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext


class Keyring:
    """
    Secure keyring system for managing encrypted API keys and sensitive data.

    This class provides secure storage and retrieval of sensitive information
    using PIN-based encryption with the EncryptionService.
    """

    def __init__(self, base_path: Path | None = None):
        """
        Initialize the keyring system.

        Args:
            base_path: Base path for the keyring directory. Defaults to ~/.anivault

        Raises:
            ApplicationError: If keyring directory cannot be created or secured
        """
        if base_path is None:
            home_dir = Path.home()
            self.base_path = home_dir / FileSystem.HOME_DIR
        else:
            self.base_path = Path(base_path)

        self.keys_dir = self.base_path / "keys"
        self.salt_file = self.base_path / "salt"

        # Initialize keyring directory structure
        self._setup_keyring_directory()

        # Load or generate salt
        self._salt = self._load_or_generate_salt()

    def _setup_keyring_directory(self) -> None:
        """
        Set up the keyring directory structure with proper permissions.

        Raises:
            ApplicationError: If directory creation or permission setting fails
        """
        try:
            # Create base directory if it doesn't exist
            self.base_path.mkdir(mode=0o700, exist_ok=True)

            # Create keys directory if it doesn't exist
            self.keys_dir.mkdir(mode=0o700, exist_ok=True)

            # Set secure permissions (700 = owner read/write/execute only)
            os.chmod(self.base_path, 0o700)
            os.chmod(self.keys_dir, 0o700)

        except PermissionError as e:
            raise ApplicationError(
                ErrorCode.PERMISSION_DENIED,
                f"Cannot create keyring directory: {self.base_path}",
                ErrorContext(operation="setup_keyring_directory"),
                original_error=e,
            ) from e
        except Exception as e:
            raise ApplicationError(
                ErrorCode.CONFIG_ERROR,
                f"Failed to setup keyring directory: {e}",
                ErrorContext(operation="setup_keyring_directory"),
                original_error=e,
            ) from e

    def _load_or_generate_salt(self) -> bytes:
        """
        Load existing salt or generate a new one.

        Returns:
            Salt bytes for key derivation

        Raises:
            ApplicationError: If salt cannot be loaded or generated
        """
        try:
            if self.salt_file.exists():
                # Load existing salt
                with open(self.salt_file, "rb") as f:
                    salt = f.read()

                # Validate salt length
                if len(salt) < 16:
                    # Salt is corrupted, regenerate it
                    salt = EncryptionService.generate_salt()

                    # Save new salt to file with secure permissions
                    with open(self.salt_file, "wb") as f:
                        f.write(salt)

                    # Set secure permissions (600 = owner read/write only)
                    os.chmod(self.salt_file, 0o600)

                return salt
            # Generate new salt
            salt = EncryptionService.generate_salt()

            # Save salt to file with secure permissions
            with open(self.salt_file, "wb") as f:
                f.write(salt)

            # Set secure permissions (600 = owner read/write only)
            os.chmod(self.salt_file, 0o600)

            return salt

        except Exception as e:
            raise ApplicationError(
                ErrorCode.CONFIG_ERROR,
                f"Failed to load or generate salt: {e}",
                ErrorContext(operation="load_or_generate_salt"),
                original_error=e,
            ) from e

    def save_key(self, key_name: str, value: str, pin: str) -> None:
        """
        Save an encrypted key-value pair to the keyring.

        Args:
            key_name: Name identifier for the key
            value: Sensitive value to encrypt and store
            pin: PIN for encryption key derivation

        Raises:
            ApplicationError: If key cannot be saved
            ValueError: If key_name or value is invalid
        """
        if not key_name or not isinstance(key_name, str):
            raise ValueError("Key name must be a non-empty string")

        if not value or not isinstance(value, str):
            raise ValueError("Value must be a non-empty string")

        if not pin or not isinstance(pin, str):
            raise ValueError("PIN must be a non-empty string")

        try:
            # Initialize encryption service with PIN and salt
            encryption_service = EncryptionService(pin, self._salt)

            # Encrypt the value
            encrypted_value = encryption_service.encrypt(value)

            # Save encrypted value to file
            key_file = self.keys_dir / key_name
            with open(key_file, "w", encoding="utf-8") as f:
                f.write(encrypted_value)

            # Set secure permissions (600 = owner read/write only)
            os.chmod(key_file, 0o600)

        except Exception as e:
            raise ApplicationError(
                ErrorCode.CONFIG_ERROR,
                f"Failed to save key '{key_name}': {e}",
                ErrorContext(
                    operation="save_key",
                    additional_data={"key_name": key_name},
                ),
                original_error=e,
            ) from e

    def load_key(self, key_name: str, pin: str) -> str:
        """
        Load and decrypt a key from the keyring.

        Args:
            key_name: Name identifier for the key
            pin: PIN for decryption key derivation

        Returns:
            Decrypted value

        Raises:
            ApplicationError: If key cannot be loaded
            DecryptionError: If decryption fails (wrong PIN)
            FileNotFoundError: If key does not exist
            ValueError: If key_name is invalid
        """
        if not key_name or not isinstance(key_name, str):
            raise ValueError("Key name must be a non-empty string")

        if not pin or not isinstance(pin, str):
            raise ValueError("PIN must be a non-empty string")

        key_file = self.keys_dir / key_name

        if not key_file.exists():
            msg = f"Key '{key_name}' not found in keyring"
            raise FileNotFoundError(msg)

        try:
            # Read encrypted value from file
            with open(key_file, encoding="utf-8") as f:
                encrypted_value = f.read()

            # Initialize encryption service with PIN and salt
            encryption_service = EncryptionService(pin, self._salt)

            # Decrypt the value
            decrypted_value = encryption_service.decrypt(encrypted_value)

            return decrypted_value

        except DecryptionError as e:
            # Re-raise decryption errors (wrong PIN)
            msg = f"Failed to decrypt key '{key_name}': Invalid PIN"
            raise DecryptionError(
                msg,
                ErrorContext(
                    operation="load_key",
                    additional_data={"key_name": key_name},
                ),
                original_error=e,
            ) from e
        except Exception as e:
            raise ApplicationError(
                ErrorCode.CONFIG_ERROR,
                f"Failed to load key '{key_name}': {e}",
                ErrorContext(
                    operation="load_key",
                    additional_data={"key_name": key_name},
                ),
                original_error=e,
            ) from e

    def delete_key(self, key_name: str) -> None:
        """
        Delete a key from the keyring.

        Args:
            key_name: Name identifier for the key

        Raises:
            ApplicationError: If key cannot be deleted
            FileNotFoundError: If key does not exist
            ValueError: If key_name is invalid
        """
        if not key_name or not isinstance(key_name, str):
            raise ValueError("Key name must be a non-empty string")

        key_file = self.keys_dir / key_name

        if not key_file.exists():
            msg = f"Key '{key_name}' not found in keyring"
            raise FileNotFoundError(msg)

        try:
            key_file.unlink()
        except Exception as e:
            raise ApplicationError(
                ErrorCode.CONFIG_ERROR,
                f"Failed to delete key '{key_name}': {e}",
                ErrorContext(
                    operation="delete_key",
                    additional_data={"key_name": key_name},
                ),
                original_error=e,
            ) from e

    def list_keys(self) -> list[str]:
        """
        List all keys in the keyring.

        Returns:
            List of key names

        Raises:
            ApplicationError: If keyring directory cannot be accessed
        """
        try:
            if not self.keys_dir.exists():
                return []

            # Get all files in keys directory
            key_files = [f.name for f in self.keys_dir.iterdir() if f.is_file()]
            return sorted(key_files)

        except Exception as e:
            raise ApplicationError(
                ErrorCode.CONFIG_ERROR,
                f"Failed to list keys: {e}",
                ErrorContext(operation="list_keys"),
                original_error=e,
            ) from e

    def key_exists(self, key_name: str) -> bool:
        """
        Check if a key exists in the keyring.

        Args:
            key_name: Name identifier for the key

        Returns:
            True if key exists, False otherwise

        Raises:
            ValueError: If key_name is invalid
        """
        if not key_name or not isinstance(key_name, str):
            raise ValueError("Key name must be a non-empty string")

        key_file = self.keys_dir / key_name
        return key_file.exists()

    def get_keyring_info(self) -> dict:
        """
        Get information about the keyring system.

        Returns:
            Dictionary with keyring information
        """
        return {
            "base_path": str(self.base_path),
            "keys_directory": str(self.keys_dir),
            "salt_file": str(self.salt_file),
            "salt_exists": self.salt_file.exists(),
            "keys_count": len(self.list_keys()),
        }
