"""Fallback strategies for matching engine.

This module provides the Strategy Pattern implementation for handling
fallback scenarios when initial matching doesn't produce satisfactory results.
"""

from __future__ import annotations

from .base import FallbackStrategy
from .genre_boost import GenreBoostStrategy
from .partial_match import PartialMatchStrategy

__all__ = [
    "FallbackStrategy",
    "GenreBoostStrategy",
    "PartialMatchStrategy",
]
