"""Business rules constants."""


class BusinessRules:
    """Business logic constants."""

    # Score thresholds
    HIGH_SCORE_THRESHOLD = 8.5
    MEDIUM_SCORE_THRESHOLD = 6.0
    LOW_SCORE_THRESHOLD = 4.0

    # Title length limits
    MAX_TITLE_LENGTH = 100
    MIN_TITLE_LENGTH = 1

    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.9
    MEDIUM_CONFIDENCE_THRESHOLD = 0.7
    LOW_CONFIDENCE_THRESHOLD = 0.5

    # Matching thresholds
    EXACT_MATCH_THRESHOLD = 0.95
    FUZZY_MATCH_THRESHOLD = 0.8
    MIN_MATCH_THRESHOLD = 0.3
