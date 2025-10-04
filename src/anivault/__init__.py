"""
AniVault - Anime Collection Management System

A comprehensive anime collection management system with metadata extraction,
TMDB integration, and advanced file organization capabilities.
"""

__version__ = "0.1.0"
__author__ = "AniVault Team"
__email__ = "contact@anivault.dev"

# Core modules
# CLI utilities
from .core import BoundedQueue, StatisticsCollector, get_statistics_collector

# Other modules will be imported when they are implemented

__all__ = [
    "BoundedQueue",
    "StatisticsCollector",
    "get_statistics_collector",
    # "AnimeScanner",
    # "MetadataParser",
    # "TMDBClient",
]
