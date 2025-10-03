"""
CLI Configuration Constants

This module contains all constants related to command-line interface
configuration, default values, and user interaction settings.
"""

from .system import Batch, Process


class WorkerConfig:
    """Worker configuration constants."""

    # Worker limits
    DEFAULT = Process.DEFAULT_WORKERS  # 4
    MIN = 1
    MAX = Process.MAX_CONCURRENT  # 16


class QueueConfig:
    """Queue configuration constants."""

    DEFAULT_SIZE = 100


class CacheConfig:
    """Cache configuration constants."""

    DEFAULT_DIR = "cache"


class ConfidenceConfig:
    """Confidence threshold configuration."""

    DEFAULT_THRESHOLD = 0.8


class BatchConfig:
    """Batch processing configuration."""

    DEFAULT_SIZE = Batch.DEFAULT_SIZE  # 50


class CLIMessages:
    """CLI message templates."""

    class Error:
        """Error message templates."""

        SCAN = "[red]Error during scan: {e}[/red]"
        MATCH = "[red]Error during matching: {e}[/red]"
        ORGANIZE = "[red]Error during organization: {e}[/red]"
        VERIFY = "[red]Error during verification: {e}[/red]"
        DIRECTORY_NOT_EXISTS = "Error: Directory '{directory}' does not exist"
        NOT_DIRECTORY = "Error: '{path}' is not a directory"
        SCAN_FAILED = "Error during scan: {error}"
        VERIFICATION_FAILED = "Error during verification: {error}"
        TMDB_CONNECTIVITY_FAILED = "✗ TMDB API connectivity failed: {error}"
        LISTING_LOGS = "Error listing logs: {error}"

    class Success:
        """Success message templates."""

        SCAN = "[green]Scan completed successfully[/green]"
        MATCH = "[green]Matching completed successfully[/green]"
        ORGANIZE = "[green]Organization completed successfully[/green]"
        RESULTS_SAVED = "Results saved to: {path}"
        SCANNING = "Scanning directory: {directory}"

    class Info:
        """Info message templates."""

        SCANNING = "[blue]Scanning directory: {directory}[/blue]"
        MATCHING = "[blue]Matching anime files in: {directory}[/blue]"
        ORGANIZING = "[blue]Organizing files in: {directory}[/blue]"
        APPLICATION_INTERRUPTED = "Application interrupted by user"
        UNEXPECTED_ERROR = "Unexpected error occurred"
        NO_OPERATION_LOGS = "No operation logs found"
        TOTAL_LOGS = "Total logs: {count}"

    class Warning:
        """Warning message templates."""

        LOW_CONFIDENCE = "[yellow]Low confidence match: {confidence:.2f}[/yellow]"
        NO_MATCHES = "[yellow]No matches found for file: {filename}[/yellow]"


class CLIFormatting:
    """CLI formatting constants."""

    INDENT_SIZE = 2
    SEPARATOR_LENGTH = 60
    DEFAULT_RATE_LIMIT_HELP = "35.0"
    DEFAULT_WORKERS_EXAMPLE = 8
    DEFAULT_RATE_LIMIT_EXAMPLE = 20


class LogConfig:
    """Logging configuration constants."""

    DEFAULT_LEVEL = "INFO"


# Backward compatibility aliases
DEFAULT_WORKERS = WorkerConfig.DEFAULT
MIN_WORKERS = WorkerConfig.MIN
MAX_WORKERS = WorkerConfig.MAX
DEFAULT_QUEUE_SIZE = QueueConfig.DEFAULT_SIZE
DEFAULT_CACHE_DIR = CacheConfig.DEFAULT_DIR
DEFAULT_CONFIDENCE_THRESHOLD = ConfidenceConfig.DEFAULT_THRESHOLD
DEFAULT_BATCH_SIZE = BatchConfig.DEFAULT_SIZE
DEFAULT_LOG_LEVEL = LogConfig.DEFAULT_LEVEL

# Message aliases
ERROR_SCAN_MESSAGE = CLIMessages.Error.SCAN
ERROR_MATCH_MESSAGE = CLIMessages.Error.MATCH
ERROR_ORGANIZE_MESSAGE = CLIMessages.Error.ORGANIZE
ERROR_VERIFY_MESSAGE = CLIMessages.Error.VERIFY
SUCCESS_SCAN_MESSAGE = CLIMessages.Success.SCAN
SUCCESS_MATCH_MESSAGE = CLIMessages.Success.MATCH
SUCCESS_ORGANIZE_MESSAGE = CLIMessages.Success.ORGANIZE
INFO_SCANNING_MESSAGE = CLIMessages.Info.SCANNING
INFO_MATCHING_MESSAGE = CLIMessages.Info.MATCHING
INFO_ORGANIZING_MESSAGE = CLIMessages.Info.ORGANIZING
WARNING_LOW_CONFIDENCE = CLIMessages.Warning.LOW_CONFIDENCE
WARNING_NO_MATCHES = CLIMessages.Warning.NO_MATCHES

# CLI specific aliases
CLI_INDENT_SIZE = CLIFormatting.INDENT_SIZE
CLI_SEPARATOR_LENGTH = CLIFormatting.SEPARATOR_LENGTH
CLI_DEFAULT_RATE_LIMIT_HELP = CLIFormatting.DEFAULT_RATE_LIMIT_HELP
CLI_DEFAULT_WORKERS_EXAMPLE = CLIFormatting.DEFAULT_WORKERS_EXAMPLE
CLI_DEFAULT_RATE_LIMIT_EXAMPLE = CLIFormatting.DEFAULT_RATE_LIMIT_EXAMPLE
CLI_ERROR_DIRECTORY_NOT_EXISTS = CLIMessages.Error.DIRECTORY_NOT_EXISTS
CLI_ERROR_NOT_DIRECTORY = CLIMessages.Error.NOT_DIRECTORY
CLI_ERROR_SCAN_FAILED = CLIMessages.Error.SCAN_FAILED
CLI_ERROR_VERIFICATION_FAILED = CLIMessages.Error.VERIFICATION_FAILED
CLI_ERROR_TMDB_CONNECTIVITY_FAILED = CLIMessages.Error.TMDB_CONNECTIVITY_FAILED
CLI_ERROR_LISTING_LOGS = CLIMessages.Error.LISTING_LOGS
CLI_SUCCESS_RESULTS_SAVED = CLIMessages.Success.RESULTS_SAVED
CLI_SUCCESS_SCANNING = CLIMessages.Success.SCANNING
CLI_INFO_APPLICATION_INTERRUPTED = CLIMessages.Info.APPLICATION_INTERRUPTED
CLI_INFO_UNEXPECTED_ERROR = CLIMessages.Info.UNEXPECTED_ERROR
CLI_INFO_NO_OPERATION_LOGS = CLIMessages.Info.NO_OPERATION_LOGS
CLI_INFO_TOTAL_LOGS = CLIMessages.Info.TOTAL_LOGS
