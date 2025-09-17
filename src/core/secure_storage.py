"""
Secure storage implementation for AniVault application.

This module provides advanced security features for storing sensitive configuration
data including encryption, key management, and secure data handling.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
import threading
from pathlib import Path
from typing import Any, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class SecureKeyManager:
    """Manages encryption keys and provides secure key operations."""

    def __init__(self, key_file_path: Optional[Path] = None):
        """
        Initialize the secure key manager.

        Args:
            key_file_path: Path to store the encryption key. If None, uses default location.
        """
        if key_file_path is None:
            self.key_file_path = Path("data/config/.encryption_key")
        else:
            self.key_file_path = Path(key_file_path)

        self._key: Optional[bytes] = None
        self._lock = threading.RLock()
        self._load_or_generate_key()

    def _load_or_generate_key(self) -> None:
        """Load existing key or generate a new one."""
        with self._lock:
            if self.key_file_path.exists():
                try:
                    with open(self.key_file_path, "rb") as f:
                        key_data = f.read()

                    # Extract key from stored data (salt + key)
                    if len(key_data) > 16:  # salt is 16 bytes
                        self._key = key_data[16:]  # Extract key part
                    else:
                        # Fallback for old format or corrupted data
                        self._key = key_data

                    logger.info("Encryption key loaded from: %s", self.key_file_path)
                except Exception as e:
                    logger.error("Failed to load encryption key: %s", str(e))
                    self._generate_new_key()
            else:
                self._generate_new_key()

    def _generate_new_key(self) -> None:
        """Generate a new encryption key."""
        try:
            # Generate a random salt
            salt = os.urandom(16)

            # Generate a random password
            password = secrets.token_urlsafe(32).encode()

            # Derive key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))

            # Store key with salt
            key_data = salt + key

            # Ensure directory exists
            self.key_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Save key with restricted permissions
            with open(self.key_file_path, "wb") as f:
                f.write(key_data)

            # Set restrictive file permissions (Unix-like systems)
            try:
                os.chmod(self.key_file_path, 0o600)
            except OSError:
                pass  # Ignore on Windows

            self._key = key
            logger.info("New encryption key generated and saved")

        except Exception as e:
            logger.error("Failed to generate encryption key: %s", str(e))
            # Fallback to simple key generation
            self._key = Fernet.generate_key()

    def get_key(self) -> bytes:
        """Get the current encryption key."""
        with self._lock:
            if self._key is None:
                self._load_or_generate_key()
            return self._key

    def rotate_key(self) -> bool:
        """
        Rotate the encryption key.

        Returns:
            True if key rotation was successful, False otherwise
        """
        with self._lock:
            try:
                old_key = self._key
                self._generate_new_key()
                logger.info("Encryption key rotated successfully")
                return True
            except Exception as e:
                logger.error("Failed to rotate encryption key: %s", str(e))
                return False


class SecureStorage:
    """
    Advanced secure storage with encryption and key management.

    This class provides secure storage capabilities for sensitive configuration
    data with automatic encryption/decryption and key management.
    """

    def __init__(self, key_manager: Optional[SecureKeyManager] = None):
        """
        Initialize the secure storage.

        Args:
            key_manager: SecureKeyManager instance. If None, creates a new one.
        """
        self.key_manager = key_manager or SecureKeyManager()
        self._lock = threading.RLock()
        self._cipher_suite: Optional[Fernet] = None
        self._initialize_cipher()

    def _initialize_cipher(self) -> None:
        """Initialize the Fernet cipher suite."""
        with self._lock:
            try:
                key = self.key_manager.get_key()
                self._cipher_suite = Fernet(key)
            except Exception as e:
                logger.error("Failed to initialize cipher suite: %s", str(e))
                self._cipher_suite = None

    def encrypt_data(self, data: str) -> str:
        """
        Encrypt sensitive data.

        Args:
            data: The data to encrypt

        Returns:
            Base64-encoded encrypted data
        """
        if data is None:
            return ""
        if not data:
            return data

        with self._lock:
            try:
                if self._cipher_suite is None:
                    self._initialize_cipher()

                if self._cipher_suite is None:
                    logger.error("Cipher suite not available, using base64 fallback")
                    return base64.b64encode(data.encode("utf-8")).decode("utf-8")

                # Encrypt the data
                encrypted_bytes = self._cipher_suite.encrypt(data.encode("utf-8"))
                return base64.b64encode(encrypted_bytes).decode("utf-8")

            except Exception as e:
                logger.error("Failed to encrypt data: %s", str(e))
                # Fallback to base64 encoding
                return base64.b64encode(data.encode("utf-8")).decode("utf-8")

    def decrypt_data(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive data.

        Args:
            encrypted_data: Base64-encoded encrypted data

        Returns:
            Decrypted data
        """
        if encrypted_data is None:
            return ""
        if not encrypted_data:
            return encrypted_data

        with self._lock:
            try:
                if self._cipher_suite is None:
                    self._initialize_cipher()

                if self._cipher_suite is None:
                    logger.error("Cipher suite not available, using base64 fallback")
                    return base64.b64decode(encrypted_data.encode("utf-8")).decode("utf-8")

                # Decode from base64
                encrypted_bytes = base64.b64decode(encrypted_data.encode("utf-8"))

                # Decrypt the data
                decrypted_bytes = self._cipher_suite.decrypt(encrypted_bytes)
                return decrypted_bytes.decode("utf-8")

            except Exception as e:
                logger.error("Failed to decrypt data: %s", str(e))
                # Re-raise the exception to be handled by the caller
                raise

    def hash_data(self, data: str) -> str:
        """
        Create a secure hash of data for integrity checking.

        Args:
            data: The data to hash

        Returns:
            SHA-256 hash of the data
        """
        if not data:
            return ""

        try:
            return hashlib.sha256(data.encode("utf-8")).hexdigest()
        except Exception as e:
            logger.error("Failed to hash data: %s", str(e))
            return ""

    def verify_data_integrity(self, data: str, expected_hash: str) -> bool:
        """
        Verify data integrity using hash comparison.

        Args:
            data: The data to verify
            expected_hash: The expected hash value

        Returns:
            True if data integrity is verified, False otherwise
        """
        if not data or not expected_hash:
            return False

        try:
            actual_hash = self.hash_data(data)
            return actual_hash == expected_hash
        except Exception as e:
            logger.error("Failed to verify data integrity: %s", str(e))
            return False

    def secure_store(self, key: str, value: str, include_hash: bool = True) -> dict[str, Any]:
        """
        Securely store a value with optional integrity checking.

        Args:
            key: The key to store the value under
            value: The value to store
            include_hash: Whether to include integrity hash

        Returns:
            Dictionary containing encrypted data and metadata
        """
        with self._lock:
            try:
                encrypted_value = self.encrypt_data(value)
                result = {
                    "encrypted_value": encrypted_value,
                    "key": key,
                    "timestamp": self._get_timestamp(),
                }

                if include_hash:
                    result["hash"] = self.hash_data(value)

                return result

            except Exception as e:
                logger.error("Failed to secure store data: %s", str(e))
                return {}

    def secure_retrieve(
        self, stored_data: dict[str, Any], verify_integrity: bool = True
    ) -> Optional[str]:
        """
        Securely retrieve a value with optional integrity verification.

        Args:
            stored_data: Dictionary containing encrypted data and metadata
            verify_integrity: Whether to verify data integrity

        Returns:
            Decrypted value or None if retrieval/verification failed
        """
        with self._lock:
            try:
                encrypted_value = stored_data.get("encrypted_value")
                if not encrypted_value:
                    return None

                # Try to decrypt the data
                try:
                    decrypted_value = self.decrypt_data(encrypted_value)
                except Exception as decrypt_error:
                    logger.error("Failed to decrypt data: %s", str(decrypt_error))
                    return None

                if verify_integrity and "hash" in stored_data:
                    expected_hash = stored_data["hash"]
                    if not self.verify_data_integrity(decrypted_value, expected_hash):
                        logger.error(
                            "Data integrity verification failed for key: %s", stored_data.get("key")
                        )
                        return None

                return decrypted_value

            except Exception as e:
                logger.error("Failed to secure retrieve data: %s", str(e))
                return None

    def _get_timestamp(self) -> str:
        """Get current timestamp as string."""
        from datetime import datetime

        return datetime.now().isoformat()

    def rotate_encryption_key(self) -> bool:
        """
        Rotate the encryption key.

        Returns:
            True if key rotation was successful, False otherwise
        """
        with self._lock:
            try:
                success = self.key_manager.rotate_key()
                if success:
                    self._initialize_cipher()
                return success
            except Exception as e:
                logger.error("Failed to rotate encryption key: %s", str(e))
                return False


# Global secure storage instance
_secure_storage: Optional[SecureStorage] = None


def get_secure_storage() -> SecureStorage:
    """
    Get the global secure storage instance.

    Returns:
        Global SecureStorage instance
    """
    global _secure_storage
    if _secure_storage is None:
        _secure_storage = SecureStorage()
    return _secure_storage


def initialize_secure_storage(key_file_path: Optional[Path] = None) -> SecureStorage:
    """
    Initialize the global secure storage.

    Args:
        key_file_path: Path to encryption key file

    Returns:
        Initialized SecureStorage instance
    """
    global _secure_storage
    key_manager = SecureKeyManager(key_file_path)
    _secure_storage = SecureStorage(key_manager)
    return _secure_storage
