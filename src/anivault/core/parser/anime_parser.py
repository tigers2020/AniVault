"""Main anime filename parser that orchestrates multiple parsing strategies.

This module provides the primary interface for parsing anime filenames,
combining anitopy and regex-based fallback strategies.
"""

from __future__ import annotations

import logging

from anivault.core.parser.anitopy_parser import AnitopyParser
from anivault.core.parser.fallback_parser import FallbackParser
from anivault.core.parser.models import ParsingResult
from anivault.shared.constants.core import BusinessRules

logger = logging.getLogger(__name__)


class AnimeFilenameParser:
    """Main parser that orchestrates multiple parsing strategies.

    This parser combines the anitopy library (primary) with a regex-based
    fallback parser (secondary) to provide robust anime filename parsing.

    The parsing strategy:
    1. Try anitopy parser first (high accuracy for standard formats)
    2. If result is insufficient, fall back to regex parser
    3. Return the best available result with appropriate confidence score

    Examples:
        >>> parser = AnimeFilenameParser()
        >>> result = parser.parse("[SubsPlease] Anime - 01 (1080p).mkv")
        >>> result.title
        'Anime'
        >>> result.episode
        1
        >>> result.parser_used
        'anitopy'
    """

    anitopy_parser: AnitopyParser | None
    fallback_parser: FallbackParser
    _has_anitopy: bool

    def __init__(self) -> None:
        """Initialize the anime filename parser with both strategies."""
        try:
            self.anitopy_parser = AnitopyParser()
            self._has_anitopy = True
        except ImportError:
            logger.warning("anitopy not available, using fallback only")
            self.anitopy_parser = None
            self._has_anitopy = False

        self.fallback_parser = FallbackParser()

    def parse(self, filename: str) -> ParsingResult:
        """Parse an anime filename using the best available strategy.

        Args:
            filename: The anime filename to parse (with or without extension).

        Returns:
            ParsingResult containing extracted metadata with confidence score.

        Examples:
            >>> parser = AnimeFilenameParser()
            >>> result = parser.parse("Attack on Titan S02E05.mkv")
            >>> result.season
            2
            >>> result.episode
            5
        """
        # Try anitopy first if available
        if self._has_anitopy and self.anitopy_parser is not None:
            result = self.anitopy_parser.parse(filename)

            # Check if result is valid and sufficient
            if self._is_valid_result(result):
                logger.debug(
                    "Using anitopy result for: %s (confidence: %.2f)",
                    filename,
                    result.confidence,
                )
                return result

            logger.debug(
                "Anitopy result insufficient for: %s, trying fallback",
                filename,
            )

        # Use fallback parser
        result = self.fallback_parser.parse(filename)

        logger.debug(
            "Using fallback result for: %s (confidence: %.2f)",
            filename,
            result.confidence,
        )

        return result

    def _is_valid_result(self, result: ParsingResult) -> bool:
        """Check if parsing result is valid and sufficient.

        A valid result must have:
        - A non-empty title
        - Reasonable confidence score (>= 0.5)

        Args:
            result: ParsingResult to validate.

        Returns:
            True if result is valid, False otherwise.
        """
        # Must have a title
        if not result.is_valid():
            return False

        # Must have reasonable confidence
        return not result.confidence < BusinessRules.LOW_CONFIDENCE_THRESHOLD

    @property
    def has_anitopy(self) -> bool:
        """Check if anitopy parser is available.

        Returns:
            True if anitopy is available, False otherwise.
        """
        return self._has_anitopy
