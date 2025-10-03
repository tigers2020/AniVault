"""
Security module for AniVault.

This module provides encryption and security-related functionality including
PIN-based encryption, key derivation, and secure data handling.
"""

from .encryption import DecryptionError, EncryptionService

__all__ = ["EncryptionService", "DecryptionError"]
