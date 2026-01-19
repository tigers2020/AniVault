"""Core module constants.

This module defines constants used specifically within the core module,
including parsing confidence scores, processing thresholds, and status values.

Note: For shared constants used across multiple modules, see `shared/constants/`.
"""

from anivault.shared.constants.business.processing import ConfigKeys, ProcessStatus, ProcessingThresholds


class ParsingConfidence:
    """Confidence score constants for parsing operations.

    These values represent the confidence boost given when specific
    information is successfully extracted from filenames.
    """

    # Base confidence scores for different parsing components
    TITLE_FOUND = 0.5  # Confidence boost when title is found
    TITLE_FOUND_FALLBACK = 0.4  # Confidence boost for fallback parser
    EPISODE_FOUND = 0.3  # Confidence boost when episode number is found
    SEASON_FOUND = 0.1  # Confidence boost when season number is found
    RESOLUTION_DETECTED = 0.8  # Confidence when resolution is successfully detected

    # Error case confidence scores
    ERROR_CONFIDENCE_ANITOPY = 0.1  # Confidence for anitopy parser error cases
    ERROR_CONFIDENCE_FALLBACK = 0.2  # Confidence for fallback parser error cases

    # Metadata bonus scores
    METADATA_BONUS = 0.05  # Small bonus for each metadata field found
    METADATA_BONUS_MAX = 0.1  # Maximum bonus for metadata fields
    METADATA_BONUS_MULTIPLIER = 0.02  # Multiplier for metadata bonus calculation


__all__ = [
    "ConfigKeys",
    "ParsingConfidence",
    "ProcessStatus",
    "ProcessingThresholds",
]
