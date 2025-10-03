"""
CLI Configuration Constants

This module contains all constants related to command-line interface
configuration, default values, and user interaction settings.
"""

# Worker Configuration
DEFAULT_WORKERS = 4  # default number of worker threads
MIN_WORKERS = 1  # minimum allowed workers
MAX_WORKERS = 16  # maximum allowed workers

# Queue Configuration
DEFAULT_QUEUE_SIZE = 100  # default maximum queue size

# Cache Directory
DEFAULT_CACHE_DIR = "cache"  # default cache directory name

# Confidence Thresholds
DEFAULT_CONFIDENCE_THRESHOLD = 0.8  # default confidence threshold for matching

# File Processing
DEFAULT_BATCH_SIZE = 50  # default batch size for file processing

# CLI Messages
ERROR_SCAN_MESSAGE = "[red]Error during scan: {e}[/red]"
ERROR_MATCH_MESSAGE = "[red]Error during matching: {e}[/red]"
ERROR_ORGANIZE_MESSAGE = "[red]Error during organization: {e}[/red]"
ERROR_VERIFY_MESSAGE = "[red]Error during verification: {e}[/red]"

# Success Messages
SUCCESS_SCAN_MESSAGE = "[green]Scan completed successfully[/green]"
SUCCESS_MATCH_MESSAGE = "[green]Matching completed successfully[/green]"
SUCCESS_ORGANIZE_MESSAGE = "[green]Organization completed successfully[/green]"

# Info Messages
INFO_SCANNING_MESSAGE = "[blue]Scanning directory: {directory}[/blue]"
INFO_MATCHING_MESSAGE = "[blue]Matching anime files in: {directory}[/blue]"
INFO_ORGANIZING_MESSAGE = "[blue]Organizing files in: {directory}[/blue]"

# Warning Messages
WARNING_LOW_CONFIDENCE = "[yellow]Low confidence match: {confidence:.2f}[/yellow]"
WARNING_NO_MATCHES = "[yellow]No matches found for file: {filename}[/yellow]"

# CLI Output and Formatting
CLI_INDENT_SIZE = 2  # JSON indent size for CLI output
CLI_SEPARATOR_LENGTH = 60  # length of separator lines
CLI_DEFAULT_RATE_LIMIT_HELP = "35.0"  # default rate limit value in help text
CLI_DEFAULT_WORKERS_EXAMPLE = 8  # default workers value in examples
CLI_DEFAULT_RATE_LIMIT_EXAMPLE = 20  # default rate limit value in examples

# CLI Error Messages
CLI_ERROR_DIRECTORY_NOT_EXISTS = "Error: Directory '{directory}' does not exist"
CLI_ERROR_NOT_DIRECTORY = "Error: '{path}' is not a directory"
CLI_ERROR_SCAN_FAILED = "Error during scan: {error}"
CLI_ERROR_VERIFICATION_FAILED = "Error during verification: {error}"
CLI_ERROR_TMDB_CONNECTIVITY_FAILED = "✗ TMDB API connectivity failed: {error}"
CLI_ERROR_LISTING_LOGS = "Error listing logs: {error}"

# CLI Success Messages
CLI_SUCCESS_RESULTS_SAVED = "Results saved to: {path}"
CLI_SUCCESS_SCANNING = "Scanning directory: {directory}"

# CLI Info Messages
CLI_INFO_APPLICATION_INTERRUPTED = "Application interrupted by user"
CLI_INFO_UNEXPECTED_ERROR = "Unexpected error occurred"
CLI_INFO_NO_OPERATION_LOGS = "No operation logs found"
CLI_INFO_TOTAL_LOGS = "Total logs: {count}"

# Log Level
DEFAULT_LOG_LEVEL = "INFO"
