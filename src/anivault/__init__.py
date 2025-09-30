"""
AniVault - Anime Collection Management System

A comprehensive anime collection management system with metadata extraction,
TMDB integration, and advanced file organization capabilities.
"""

__version__ = "0.1.0"
__author__ = "AniVault Team"
__email__ = "contact@anivault.dev"

# Core modules
from .scanner import AnimeScanner
from .parser import MetadataParser
from .tmdb_client import TMDBClient

__all__ = [
    "AnimeScanner",
    "MetadataParser", 
    "TMDBClient",
]
