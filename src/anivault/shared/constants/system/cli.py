"""CLI-related constants."""


class CLI:
    """CLI related constants."""

    INDENT_SIZE = 2

    # Message templates
    INFO_COMMAND_STARTED = "Starting {command} command..."
    INFO_COMMAND_COMPLETED = "Completed {command} command"
    SUCCESS_RESULTS_SAVED = "Results saved to: {path}"

    # Error messages
    ERROR_SCAN_FAILED = "Scan command failed: {error}"
    ERROR_ORGANIZE_FAILED = "Organize command failed: {error}"
    ERROR_MATCH_FAILED = "Match command failed: {error}"
    ERROR_VERIFY_FAILED = "Verify command failed: {error}"
    ERROR_ROLLBACK_FAILED = "Rollback command failed: {error}"
    ERROR_TMDB_CONNECTIVITY_FAILED = "TMDB API connectivity failed: {error}"
    ERROR_VERIFICATION_FAILED = "Verification failed: {error}"


__all__ = ["CLI"]
