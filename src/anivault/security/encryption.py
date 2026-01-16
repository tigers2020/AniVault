"""
Core encryption module for AniVault.

This module provides the fundamental encryption and decryption logic using Fernet
for the secure keyring system. It implements PIN-based key derivation using
PBKDF2-HMAC-SHA256 for strong security.
"""

from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from anivault.shared.errors import (
    ApplicationError,
    ErrorCode,
    ErrorContextModel,
    SecurityError,
)


class DecryptionError(ApplicationError):
    """Raised when decryption fails due to invalid token or key."""

    def __init__(
        self,
        message: str = "Decryption failed",
        context: ErrorContextModel | None = None,
        original_error: Exception | None = None,
    ):
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            context=context,
            original_error=original_error,
        )


class EncryptionService:
    """
    Service for encrypting and decrypting data using PIN-based key derivation.

    This service uses PBKDF2-HMAC-SHA256 to derive a Fernet-compatible key from
    a user PIN and salt, providing strong security for sensitive data encryption.
    """

    # PBKDF2 configuration for strong key derivation
    PBKDF2_ITERATIONS = 600000  # OWASP recommended minimum
    KEY_LENGTH = 32  # 256 bits for Fernet compatibility

    def __init__(self, pin: str, salt: bytes):
        """
        Initialize the encryption service with a PIN and salt.

        Args:
            pin: User PIN for key derivation
            salt: Random salt for key derivation

        Raises:
            ApplicationError: If key derivation fails
        """
        if not pin or not isinstance(pin, str):
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                "PIN must be a non-empty string",
                ErrorContextModel(operation="encryption_init"),
            )

        if not salt or len(salt) < 16:
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                "Salt must be at least 16 bytes",
                ErrorContextModel(operation="encryption_init"),
            )

        try:
            # Derive the encryption key from PIN and salt
            derived_key = self._derive_key(pin, salt)

            # Initialize Fernet suite with derived key
            self._fernet_suite = Fernet(derived_key)

        except Exception as e:
            raise ApplicationError(
                ErrorCode.CONFIG_ERROR,
                f"Failed to initialize encryption service: {e}",
                ErrorContextModel(operation="encryption_init"),
                original_error=e,
            ) from e

    @classmethod
    def _derive_key(cls, pin: str, salt: bytes) -> bytes:
        """
        Derive a Fernet-compatible key from PIN and salt using PBKDF2-HMAC-SHA256.

        Args:
            pin: User PIN
            salt: Random salt bytes

        Returns:
            Base64-encoded key suitable for Fernet

        Raises:
            ApplicationError: If key derivation fails
        """
        try:
            # Convert PIN to bytes using UTF-8 encoding
            pin_bytes = pin.encode("utf-8")

            # Create PBKDF2 key derivation function
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=cls.KEY_LENGTH,
                salt=salt,
                iterations=cls.PBKDF2_ITERATIONS,
                backend=default_backend(),
            )

            # Derive the key
            key = kdf.derive(pin_bytes)

            # Encode to base64 for Fernet compatibility
            return base64.urlsafe_b64encode(key)

        except Exception as e:
            raise ApplicationError(
                ErrorCode.CONFIG_ERROR,
                f"Key derivation failed: {e}",
                ErrorContextModel(operation="key_derivation"),
                original_error=e,
            ) from e

    def encrypt(self, data: str) -> str:
        """
        Encrypt plaintext data using the derived key.

        Args:
            data: Plaintext string to encrypt

        Returns:
            Encrypted token as base64-encoded string

        Raises:
            ApplicationError: If encryption fails
        """
        if data is None:
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                "Data cannot be None",
                ErrorContextModel(operation="encrypt"),
            )

        try:
            # Convert string to bytes
            data_bytes = data.encode("utf-8")

            # Encrypt the data
            encrypted_token = self._fernet_suite.encrypt(data_bytes)

            # Return as string
            return str(encrypted_token.decode("utf-8"))

        except Exception as e:
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                f"Encryption failed: {e}",
                ErrorContextModel(operation="encrypt"),
                original_error=e,
            ) from e

    def decrypt(self, token: str) -> str:
        """
        Decrypt an encrypted token back to plaintext.

        Args:
            token: Encrypted token as base64-encoded string

        Returns:
            Decrypted plaintext string

        Raises:
            DecryptionError: If decryption fails due to invalid token
            ApplicationError: If other errors occur during decryption
        """
        if not token or not isinstance(token, str):
            raise DecryptionError(
                "Token must be a non-empty string",
                ErrorContextModel(operation="decrypt"),
            )

        try:
            # Convert string token back to bytes
            token_bytes = token.encode("utf-8")

            # Decrypt the token
            decrypted_bytes = self._fernet_suite.decrypt(token_bytes)

            # Convert back to string
            return str(decrypted_bytes.decode("utf-8"))

        except InvalidToken as e:
            raise DecryptionError(
                "Invalid or tampered encryption token",
                ErrorContextModel(operation="decrypt"),
                original_error=e,
            ) from e

        except Exception as e:
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                f"Decryption failed: {e}",
                ErrorContextModel(operation="decrypt"),
                original_error=e,
            ) from e

    @classmethod
    def generate_salt(cls, length: int = 32) -> bytes:
        """
        Generate a cryptographically secure random salt.

        Args:
            length: Length of salt in bytes (default: 32)

        Returns:
            Random salt bytes

        Raises:
            ApplicationError: If salt generation fails
        """
        if length < 16:
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                "Salt length must be at least 16 bytes",
                ErrorContextModel(operation="generate_salt"),
            )

        try:
            return os.urandom(length)
        except Exception as e:
            raise ApplicationError(
                ErrorCode.CONFIG_ERROR,
                f"Salt generation failed: {e}",
                ErrorContextModel(operation="generate_salt"),
                original_error=e,
            ) from e

    def validate_token(self, token: str) -> None:
        """Validate that a token is valid and can be decrypted.

        Args:
            token: Token to validate

        Raises:
            SecurityError: If token is invalid, malformed, or expired
        """

        # Validate token is not empty
        if not token or len(token.strip()) == 0:
            raise SecurityError(
                code=ErrorCode.INVALID_TOKEN,
                message="Token is empty or None",
                context=ErrorContextModel(operation="validate_token"),
            )

        try:
            # Try to decrypt to validate
            token_bytes = token.encode("utf-8")
            self._fernet_suite.decrypt(token_bytes)
        except InvalidToken as e:
            raise SecurityError(
                code=ErrorCode.INVALID_TOKEN,
                message="Invalid or expired token",
                context=ErrorContextModel(operation="validate_token"),
                original_error=e,
            ) from e
        except Exception as e:
            raise SecurityError(
                code=ErrorCode.INVALID_TOKEN,
                message=f"Token validation failed: {e}",
                context=ErrorContextModel(
                    operation="validate_token",
                    additional_data={"error_type": type(e).__name__},
                ),
                original_error=e,
            ) from e
