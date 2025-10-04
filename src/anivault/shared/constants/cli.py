"""
CLI Configuration Constants

This module contains all constants related to command-line interface
configuration, default values, and user interaction settings.
"""

from typing import ClassVar, Literal

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
        APPLICATION_ERROR_DURING_SCAN = (
            "[red]Application error during scan: {error}[/red]"
        )
        INFRASTRUCTURE_ERROR_DURING_SCAN = (
            "[red]Infrastructure error during scan: {error}[/red]"
        )
        UNEXPECTED_ERROR_IN_SCAN = "[red]Unexpected error in scan command[/red]"
        APPLICATION_ERROR_IN_SCAN = "Application error in scan command"
        INFRASTRUCTURE_ERROR_IN_SCAN = "Infrastructure error in scan command"

        # Additional error messages
        VALIDATION_ERROR = "Validation error: "
        APPLICATION_ERROR = "Application error: "
        INFRASTRUCTURE_ERROR = "Infrastructure error: "
        UNEXPECTED_ERROR = "Unexpected error: "
        DIRECTORY_VALIDATION_FAILED = "Directory validation failed"
        UNEXPECTED_ERROR_DURING_VALIDATION = (
            "Unexpected error during directory validation"
        )

    class StatusKeys:
        """Common status keys used throughout CLI."""

        ERROR_CODE = "error_code"
        CONTEXT = "context"
        STATUS = "status"
        STEP = "step"
        STEPS = "steps"
        OPERATION = "operation"
        FILE_PATH = "file_path"
        DIRECTORY = "directory"
        SOURCE = "source"
        PARSING_RESULT = "parsing_result"
        ENRICHED_METADATA = "enriched_metadata"

    class CommandNames:
        """Command names used in error messages and logging."""

        SCAN = "scan"
        MATCH = "match"
        ORGANIZE = "organize"
        ROLLBACK = "rollback"
        RUN = "run"
        LOG = "log"
        VERIFY = "verify"

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

        # Additional info messages
        SCANNING_FILES = "Scanning files..."
        ENRICHING_METADATA = "Enriching metadata..."
        NO_ANIME_FILES_FOUND = "No anime files found in the specified directory"

    class WarningMessages:
        """Warning message templates."""

        LOW_CONFIDENCE = "[yellow]Low confidence match: {confidence:.2f}[/yellow]"
        NO_MATCHES = "[yellow]No matches found for file: {filename}[/yellow]"

    class Output:
        """Output formatting templates."""

        # Table headers
        SCAN_RESULTS_TITLE = "Anime File Scan Results"
        TABLE_COLUMN_TITLE = "Title"
        TABLE_COLUMN_EPISODE = "Episode"
        TABLE_COLUMN_QUALITY = "Quality"
        TABLE_COLUMN_TMDB_MATCH = "TMDB Match"
        TABLE_COLUMN_TMDB_RATING = "TMDB Rating"

        # Table column styles
        TABLE_EPISODE_STYLE = "blue"
        TABLE_TMDB_MATCH_STYLE = "yellow"

        # File info keys
        FILE_PATH_KEY = "file_path"
        FILE_NAME_KEY = "file_name"
        FILE_SIZE_KEY = "file_size"
        FILE_EXTENSION_KEY = "file_extension"

        # Parsing result keys
        PARSING_RESULT_KEY = "parsing_result"
        TITLE_KEY = "title"
        EPISODE_KEY = "episode"
        SEASON_KEY = "season"
        QUALITY_KEY = "quality"
        SOURCE_KEY = "source"
        CODEC_KEY = "codec"
        AUDIO_KEY = "audio"
        RELEASE_GROUP_KEY = "release_group"
        CONFIDENCE_KEY = "confidence"
        PARSER_USED_KEY = "parser_used"
        OTHER_INFO_KEY = "other_info"

        # Enriched metadata keys
        ENRICHED_METADATA_KEY = "enriched_metadata"
        ENRICHMENT_STATUS_KEY = "enrichment_status"
        MATCH_CONFIDENCE_KEY = "match_confidence"
        TMDB_DATA_KEY = "tmdb_data"

        # JSON output keys
        SCAN_SUMMARY_KEY = "scan_summary"
        TOTAL_FILES_KEY = "total_files"
        TOTAL_SIZE_BYTES_KEY = "total_size_bytes"
        TOTAL_SIZE_FORMATTED_KEY = "total_size_formatted"
        SCANNED_DIRECTORY_KEY = "scanned_directory"
        METADATA_ENRICHED_KEY = "metadata_enriched"
        FILE_STATISTICS_KEY = "file_statistics"
        COUNTS_BY_EXTENSION_KEY = "counts_by_extension"
        SCANNED_PATHS_KEY = "scanned_paths"
        FILES_KEY = "files"

        # Default values
        UNKNOWN_VALUE = "Unknown"
        NO_MATCH_VALUE = "No match"

        # Size formatting
        SIZE_PB_SUFFIX = " PB"


class CLIFormatting:
    """CLI formatting constants."""

    INDENT_SIZE = 2
    SEPARATOR_LENGTH = 60
    DEFAULT_RATE_LIMIT_HELP = "35.0"
    DEFAULT_WORKERS_EXAMPLE = 8
    DEFAULT_RATE_LIMIT_EXAMPLE = 20

    # Semantic color system
    class Colors:
        """Semantic color definitions."""

        # Primary colors
        PRIMARY = "[bold blue]"
        SECONDARY = "[dim blue]"

        # Status colors
        INFO = "[blue]"
        WARNING = "[yellow]"
        ERROR = "[red]"
        SUCCESS = "[green]"

        # Reset tag
        RESET = "[/]"

    # Legacy color tags (for backward compatibility)
    COLOR_RED = "[red]"
    COLOR_GREEN = "[green]"
    COLOR_BLUE = "[blue]"
    COLOR_YELLOW = "[yellow]"
    COLOR_RESET = "[/]"

    @staticmethod
    def format_colored_message(message: str, color_type: str) -> str:
        """Format a message with semantic color.

        Args:
            message: The message to format
            color_type: Color type (primary, secondary, info, warning, error, success)

        Returns:
            Formatted message with color tags
        """
        color_map = {
            "primary": CLIFormatting.Colors.PRIMARY,
            "secondary": CLIFormatting.Colors.SECONDARY,
            "info": CLIFormatting.Colors.INFO,
            "warning": CLIFormatting.Colors.WARNING,
            "error": CLIFormatting.Colors.ERROR,
            "success": CLIFormatting.Colors.SUCCESS,
        }

        color_tag = color_map.get(color_type.lower(), "")
        return f"{color_tag}{message}{CLIFormatting.Colors.RESET}"


class CLIOptions:
    """CLI option names and flags."""

    # Common options
    VERBOSE = "--verbose"
    VERBOSE_SHORT = "-v"
    LOG_LEVEL = "--log-level"
    JSON = "--json"
    JSON_OUTPUT = "--json-output"
    VERSION = "--version"
    VERSION_SHORT = "-V"
    HELP = "--help"
    HELP_SHORT = "-h"

    # Scan options
    RECURSIVE = "--recursive"
    RECURSIVE_SHORT = "-r"
    INCLUDE_SUBTITLES = "--include-subtitles"
    INCLUDE_METADATA = "--include-metadata"
    OUTPUT = "--output"
    OUTPUT_SHORT = "-o"
    EXTENSIONS = "--extensions"

    # Organize options
    DRY_RUN = "--dry-run"
    YES = "--yes"
    YES_SHORT = "-y"
    ENHANCED = "--enhanced"
    DESTINATION = "--destination"
    DESTINATION_SHORT = "-d"
    SIMILARITY_THRESHOLD = "--similarity-threshold"

    # Run options
    SKIP_SCAN = "--skip-scan"
    SKIP_MATCH = "--skip-match"
    SKIP_ORGANIZE = "--skip-organize"
    MAX_WORKERS = "--max-workers"
    BATCH_SIZE = "--batch-size"

    # Log options
    LOG_DIR = "--log-dir"
    FOLLOW = "--follow"

    # Verify options
    TMDB = "--tmdb"
    ALL = "--all"


class CLICommands:
    """CLI command names."""

    SCAN = "scan"
    MATCH = "match"
    ORGANIZE = "organize"
    RUN = "run"
    LOG = "log"
    ROLLBACK = "rollback"
    VERIFY = "verify"
    INIT = "init"


class CLIHelp:
    """CLI help text and descriptions."""

    # Version
    VERSION_HELP = "Print version information and exit."
    VERSION_TEXT = "AniVault CLI v{version}"

    # App info
    APP_NAME = "anivault"
    APP_DESCRIPTION = "AniVault - Advanced Anime Collection Management System"
    APP_STYLE: Literal["rich"] = "rich"

    # Main description
    MAIN_DESCRIPTION = """
    AniVault - Advanced Anime Collection Management System.

    A comprehensive tool for organizing anime collections with TMDB integration,
    intelligent file matching, and automated organization capabilities.
    """

    # Scan command
    SCAN_HELP = "Scan directory for anime files"
    SCAN_DIRECTORY_HELP = "Directory to scan for anime files"
    SCAN_RECURSIVE_HELP = "Scan directories recursively"
    SCAN_INCLUDE_SUBTITLES_HELP = "Include subtitle files in scan"
    SCAN_INCLUDE_METADATA_HELP = "Include metadata files in scan"
    SCAN_OUTPUT_HELP = "Output file for scan results (JSON format)"
    SCAN_JSON_HELP = "Output results in JSON format"

    # Match command
    MATCH_HELP = "Match anime files against TMDB database"
    MATCH_DIRECTORY_HELP = "Directory to match anime files against TMDB database"
    MATCH_RECURSIVE_HELP = "Match files recursively in subdirectories"
    MATCH_INCLUDE_SUBTITLES_HELP = "Include subtitle files in matching"
    MATCH_INCLUDE_METADATA_HELP = "Include metadata files in matching"
    MATCH_OUTPUT_HELP = "Output file for match results (JSON format)"
    MATCH_JSON_HELP = "Output results in JSON format"

    # Organize command
    ORGANIZE_HELP = "Organize anime files into structured directories"
    ORGANIZE_DIRECTORY_HELP = (
        "Directory containing scanned and matched anime files to organize"
    )
    ORGANIZE_DRY_RUN_HELP = "Show what would be organized without actually moving files"
    ORGANIZE_YES_HELP = "Skip confirmation prompts and proceed with organization"
    ORGANIZE_JSON_HELP = "Output results in JSON format"
    ORGANIZE_DESTINATION_HELP = "Destination directory for organized files"
    ORGANIZE_DESCRIPTION = """
    Organize anime files into a structured directory layout.

    This command takes scanned and matched anime files and organizes them
    into a clean directory structure based on the TMDB metadata. It can
    create series folders, season subfolders, and rename files consistently.

    Examples:
        # Organize files in current directory (with confirmation)
        anivault organize .

        # Preview what would be organized without making changes
        anivault organize . --dry-run

        # Organize without confirmation prompts
        anivault organize . --yes
    """

    # Run command
    RUN_HELP = "Run complete pipeline: scan, match, and organize"
    RUN_DIRECTORY_HELP = "Directory containing anime files to process"
    RUN_RECURSIVE_HELP = "Process files recursively in subdirectories"
    RUN_INCLUDE_SUBTITLES_HELP = "Include subtitle files in processing"
    RUN_INCLUDE_METADATA_HELP = "Include metadata files in processing"
    RUN_OUTPUT_HELP = "Output file for processing results (JSON format)"
    RUN_DRY_RUN_HELP = "Show what would be processed without actually processing files"
    RUN_YES_HELP = "Skip confirmation prompts and proceed with processing"
    RUN_JSON_HELP = "Output results in JSON format"

    # Log command
    LOG_HELP = "Manage operation logs"
    LOG_DIR_HELP = "Directory containing log files"

    # Rollback command
    ROLLBACK_HELP = "Rollback file organization operations"
    ROLLBACK_LOG_ID_HELP = "ID of the operation log to rollback"
    ROLLBACK_DRY_RUN_HELP = (
        "Show what would be rolled back without actually moving files"
    )
    ROLLBACK_YES_HELP = "Skip confirmation prompts and proceed with rollback"
    ROLLBACK_DESCRIPTION = """
    Rollback file organization operations from a previous session.

    This command allows you to undo file organization operations by rolling back
    files to their original locations based on operation logs. It can show what
    would be rolled back without making changes using --dry-run.

    Examples:
        # Rollback operations from log ID "2024-01-15_143022"
        anivault rollback 2024-01-15_143022

        # Preview what would be rolled back without making changes
        anivault rollback 2024-01-15_143022 --dry-run

        # Rollback without confirmation prompts
        anivault rollback 2024-01-15_143022 --yes
    """

    # Verify command
    VERIFY_HELP = "Verify system components and connectivity"
    VERIFY_TMDB_HELP = "Verify TMDB API connectivity"
    VERIFY_ALL_HELP = "Verify all components"


class CLIDefaults:
    """CLI default values."""

    # Version information
    VERSION = "0.1.0"

    # Default directories
    DEFAULT_DESTINATION = "Anime"

    # Default extensions
    DEFAULT_VIDEO_EXTENSIONS: ClassVar[list[str]] = ["mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v"]

    # Default thresholds
    DEFAULT_SIMILARITY_THRESHOLD = 0.8

    # Default workers
    DEFAULT_MAX_WORKERS = 8
    DEFAULT_BATCH_SIZE = 50

    # Default boolean values
    DEFAULT_YES = False
    DEFAULT_JSON = False
    DEFAULT_DRY_RUN = False

    # Default numeric values
    DEFAULT_VERBOSE = 0
    DEFAULT_WORKER_COUNT = 4
    DEFAULT_CONCURRENCY_LIMIT = 4
    DEFAULT_SCAN_CONCURRENCY = 5
    DEFAULT_FILE_SIZE = 0

    # Exit codes
    EXIT_SUCCESS = 0
    EXIT_ERROR = 1

    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.8
    MEDIUM_CONFIDENCE_THRESHOLD = 0.6
    LOW_CONFIDENCE_THRESHOLD = 0.0

    # File size conversion
    BYTES_PER_KB = 1024.0


class RunDefaults:
    """Run command default values."""

    # Default workers and concurrency
    DEFAULT_MAX_WORKERS = 4
    DEFAULT_BATCH_SIZE = 10
    DEFAULT_RATE_LIMIT = 50
    DEFAULT_CONCURRENT = 4

    # Default destination directory
    DEFAULT_DESTINATION = "Anime"

    # Default extensions
    DEFAULT_EXTENSIONS = [
        "mkv",
        "mp4",
        "avi",
        "mov",
        "wmv",
        "flv",
        "webm",
        "m4v",
    ]


class LogConfig:
    """Logging configuration constants."""

    DEFAULT_LEVEL = "INFO"
    DEFAULT_FILENAME = "anivault.log"
