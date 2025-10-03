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

    class WarningMessages:
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
