"""Core module for AniVault application.

This module contains the core data models and business logic components.
"""

from .cache_core import CacheEntry
from .compression import CacheDeserializationError

__version__ = "0.1.0"

__all__ = [
    "CacheDeserializationError",
    "CacheEntry",
]
