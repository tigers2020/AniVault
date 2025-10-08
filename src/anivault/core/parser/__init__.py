"""Parser module for anime filename parsing.

This module provides anime filename parsing functionality using
multiple parsing strategies (anitopy, regex fallback).
"""

from anivault.core.parser.anime_parser import AnimeFilenameParser
from anivault.core.parser.models import ParsingResult

__all__ = ["AnimeFilenameParser", "ParsingResult"]
