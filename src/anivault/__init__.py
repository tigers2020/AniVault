"""
AniVault - Anime Collection Management System

A comprehensive anime collection management system with metadata extraction,
TMDB integration, and advanced file organization capabilities.
"""

__version__ = "0.1.0"
__author__ = "AniVault Team"
__email__ = "contact@anivault.dev"

# Core modules
from .core import BoundedQueue, Statistics

# Other modules will be imported when they are implemented

__all__ = [
    "BoundedQueue",
    "Statistics",
    # "AnimeScanner",
    # "MetadataParser",
    # "TMDBClient",
]
