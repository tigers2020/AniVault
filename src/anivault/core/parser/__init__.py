"""Parser module for anime filename parsing.

This module provides anime filename parsing functionality using
multiple parsing strategies (anitopy, regex fallback).

ParsingResult, ParsingAdditionalInfo: use domain.entities.parser.
"""

from anivault.core.parser.anime_parser import AnimeFilenameParser
from anivault.core.parser.helpers import parse_with_fallback

__all__ = ["AnimeFilenameParser", "parse_with_fallback"]
