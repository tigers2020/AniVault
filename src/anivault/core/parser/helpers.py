"""Common parsing helper functions for consistent error handling.

This module provides shared utilities for parsing anime filenames with
consistent error handling and fallback behavior across the codebase.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

from anivault.core.parser.models import ParsingAdditionalInfo, ParsingResult

logger = logging.getLogger(__name__)


class ParserProtocol(Protocol):
    """Protocol for parser objects that have a parse method."""

    def parse(self, filename: str) -> ParsingResult:
        """Parse a filename and return ParsingResult."""
        ...  # pylint: disable=unnecessary-ellipsis


def parse_with_fallback(
    parser: ParserProtocol,
    filename: str,
    *,
    fallback_title: str | None = None,
    fallback_parser_name: str = "fallback",
) -> ParsingResult:
    """Parse filename with consistent error handling and fallback.

    This helper function provides a standardized way to parse filenames
    with error handling across the codebase, reducing code duplication.

    Args:
        parser: Parser instance with a parse() method
        filename: Filename to parse (with or without extension)
        fallback_title: Title to use in fallback result (defaults to filename stem)
        fallback_parser_name: Name to use for parser_used field in fallback

    Returns:
        ParsingResult instance (either successful parse or fallback)

    Example:
        >>> parser = AnimeFilenameParser()
        >>> result = parse_with_fallback(parser, "anime_ep01.mkv")
        >>> result.title  # Either parsed title or "anime_ep01"
    """
    try:
        result = parser.parse(filename)
        return result
    except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught
        # Log the error for debugging
        logger.warning("Failed to parse '%s': %s", filename, e)

        # Determine fallback title
        if fallback_title is None:
            # Use filename stem as fallback
            fallback_title = Path(filename).stem if filename else "unknown"

        # Create fallback ParsingResult
        return ParsingResult(
            title=fallback_title,
            episode=None,
            season=None,
            quality=None,
            source=None,
            codec=None,
            audio=None,
            release_group=None,
            confidence=0.0,
            parser_used=fallback_parser_name,
            additional_info=ParsingAdditionalInfo(error=str(e)),
        )
