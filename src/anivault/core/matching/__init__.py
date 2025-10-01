"""Matching engine module for AniVault.

This module provides the core matching functionality for finding anime titles
in the TMDB database using various strategies and confidence scoring.
"""

from .engine import MatchingEngine

__all__ = [
    "MatchingEngine",
]
