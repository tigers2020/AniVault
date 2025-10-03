"""
Security module for AniVault.

This module provides encryption and security-related functionality including
PIN-based encryption, key derivation, and secure data handling.
"""

from .encryption import DecryptionError, EncryptionService
from .keyring import Keyring

__all__ = ["DecryptionError", "EncryptionService", "Keyring"]
