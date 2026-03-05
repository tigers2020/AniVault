"""Entity validation constants for domain layer (Phase 5).

Extracted from shared.constants for domain self-containment.
Domain layer must have no external dependencies.
"""

# Year validation
MIN_YEAR = 1900
MAX_YEAR = 2030

# Vote average validation
MIN_VOTE_AVERAGE = 0.0
MAX_VOTE_AVERAGE = 10.0

# Error messages
EMPTY_TITLE_ERROR = "title cannot be empty"
EMPTY_FILE_TYPE_ERROR = "file_type cannot be empty"

YEAR_RANGE_ERROR_TEMPLATE = f"year must be between {MIN_YEAR} and {MAX_YEAR}, got {{year}}"
SEASON_NEGATIVE_ERROR_TEMPLATE = "season must be non-negative, got {season}"
EPISODE_NEGATIVE_ERROR_TEMPLATE = "episode must be non-negative, got {episode}"
VOTE_AVERAGE_RANGE_ERROR_TEMPLATE = f"vote_average must be between {MIN_VOTE_AVERAGE} and {MAX_VOTE_AVERAGE}, got {{vote_average}}"
