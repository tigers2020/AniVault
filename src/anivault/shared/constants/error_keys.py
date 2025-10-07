"""Error Context Keys Constants.

This module contains error context field keys for consistent
error handling and reporting across the application.
"""


class ErrorContextKeys:
    """Error context dictionary keys."""

    # Primary keys
    OPERATION = "operation"
    USER_ID = "user_id"
    ADDITIONAL_DATA = "additional_data"
    ORIGINAL_ERROR = "original_error"

    # Field validation
    FIELD = "field"
    CONFIG_KEY = "config_key"

    # Output formatting
    OUTPUT_TYPE = "output_type"
    CLI_OUTPUT = "cli_output"

    # Error categorization
    ERROR_TYPE = "error_type"
    ERROR_CATEGORY = "error_category"

    # Network errors
    NETWORK = "network"
    CONNECTION = "connection"

    # Data processing
    DATA_PROCESSING = "data_processing"

    # Unexpected errors
    UNEXPECTED = "unexpected"


class ErrorCategoryValues:
    """Error category values."""

    NETWORK = "network"
    DATA_PROCESSING = "data_processing"
    VALIDATION = "validation"
    UNEXPECTED = "unexpected"
    CONNECTION = "connection"


class StatusValues:
    """Status values used throughout the application."""

    # Processing status
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

    # Enrichment status
    ENRICHED = "enriched"
    NOT_ENRICHED = "not_enriched"
    PARTIAL = "partial"

    # Match status
    MATCHED = "matched"
    NO_MATCH = "no_match"
    UNCERTAIN = "uncertain"

