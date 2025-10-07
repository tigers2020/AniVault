"""Logging Context Keys Constants.

This module contains all logging context field keys to ensure
consistency in structured logging across the application.
"""


class LogContextKeys:
    """Logging context dictionary keys."""

    # Operation tracking
    OPERATION = "operation"
    OPERATION_ID = "operation_id"

    # Media/File information
    MEDIA_ID = "media_id"
    MEDIA_TYPE = "media_type"
    FILE_PATH = "file_path"
    FILE_INDEX = "file_index"
    FILE_COUNT = "file_count"

    # Error tracking
    ORIGINAL_ERROR = "original_error"
    ERROR_TYPE = "error_type"
    ERROR_CODE = "error_code"

    # User/Session
    USER_ID = "user_id"
    SESSION_ID = "session_id"

    # Request/Response
    REQUEST_ID = "request_id"
    RESPONSE = "response"
    STATUS_CODE = "status_code"
    DURATION_MS = "duration_ms"

    # Retry and rate limiting
    RETRY_ATTEMPTS = "retry_attempts"
    RETRY_COUNT = "retry_count"

    # Search and matching
    MIN_CONFIDENCE = "min_confidence"
    MATCH_CONFIDENCE = "match_confidence"
    SEARCH_RESULTS_COUNT = "search_results_count"

    # Additional data
    ADDITIONAL_DATA = "additional_data"
    RESULT_INFO = "result_info"

    # API specific
    ENDPOINT = "endpoint"
    METHOD = "method"
    HEADER_VALUE = "header_value"


class LogOperationNames:
    """Standard operation names for logging."""

    # TMDB operations
    TMDB_SEARCH = "tmdb_search"
    GET_MEDIA_DETAILS = "get_media_details"
    MAKE_TMDB_REQUEST = "make_tmdb_request"

    # Enrichment operations
    ENRICH_METADATA = "enrich_metadata"
    ENRICH_BATCH = "enrich_batch"
    ENRICH_BATCH_ITEM = "enrich_batch_item"

    # Matching operations
    FIND_BEST_MATCH = "find_best_match"
    CALCULATE_MATCH_SCORE = "calculate_match_score"

    # File operations
    FILE_OPERATION = "file_operation"

    # Validation
    VALIDATION = "validation"
    VALIDATE_TOKEN = "validate_token"  # noqa: S105 # Operation name, not actual token
    VALIDATE_API_KEY = "validate_api_key"

    # Security operations
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"
    ENCRYPTION_INIT = "encryption_init"
    KEY_DERIVATION = "key_derivation"
    GENERATE_SALT = "generate_salt"

    # Keyring operations
    SETUP_KEYRING_DIRECTORY = "setup_keyring_directory"
    LOAD_OR_GENERATE_SALT = "load_or_generate_salt"
    SAVE_KEY = "save_key"
    LOAD_KEY = "load_key"
    DELETE_KEY = "delete_key"
    LIST_KEYS = "list_keys"

    # Permission operations
    SET_SECURE_FILE_PERMISSIONS = "set_secure_file_permissions"

    # API calls
    API_CALL = "api_call"


class LogFieldNames:
    """Log field names for structured logging."""

    LEVEL = "level"
    LOGGER = "logger"
    OPERATION = "operation"
    DURATION_MS = "duration_ms"
    RESULT_INFO = "result_info"
    EXCEPTION = "exception"

    # Validation fields
    FIELD = "field"
    VALUE = "value"
    REASON = "reason"

    # API fields
    ENDPOINT = "endpoint"
    METHOD = "method"
    STATUS_CODE = "status_code"

    # File operation fields
    SOURCE_PATH = "source_path"
    DESTINATION_PATH = "destination_path"

