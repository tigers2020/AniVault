"""CLI configuration constants (Phase 3-2 domain grouping)."""

from typing import ClassVar, Literal

from anivault.shared.constants.system import Batch, Process


class WorkerConfig:
    """Worker configuration constants."""

    DEFAULT = Process.DEFAULT_WORKERS
    MIN = 1
    MAX = Process.MAX_CONCURRENT


class QueueConfig:
    """Queue configuration constants."""

    DEFAULT_SIZE = 100


class ConfidenceConfig:
    """Confidence threshold configuration."""

    DEFAULT_THRESHOLD = 0.8


class BatchConfig:
    """Batch processing configuration."""

    DEFAULT_SIZE = Batch.DEFAULT_SIZE


class CLIOptions:
    """CLI option names and flags."""

    VERBOSE = "--verbose"
    VERBOSE_SHORT = "-v"
    LOG_LEVEL = "--log-level"
    JSON = "--json"
    JSON_OUTPUT = "--json-output"
    VERSION = "--version"
    VERSION_SHORT = "-V"
    HELP = "--help"
    HELP_SHORT = "-h"
    RECURSIVE = "--recursive"
    RECURSIVE_SHORT = "-r"
    INCLUDE_SUBTITLES = "--include-subtitles"
    INCLUDE_METADATA = "--include-metadata"
    OUTPUT = "--output"
    OUTPUT_SHORT = "-o"
    EXTENSIONS = "--extensions"
    DRY_RUN = "--dry-run"
    YES = "--yes"
    YES_SHORT = "-y"
    ENHANCED = "--enhanced"
    DESTINATION = "--destination"
    DESTINATION_SHORT = "-d"
    SIMILARITY_THRESHOLD = "--similarity-threshold"
    SKIP_SCAN = "--skip-scan"
    SKIP_MATCH = "--skip-match"
    SKIP_ORGANIZE = "--skip-organize"
    MAX_WORKERS = "--max-workers"
    BATCH_SIZE = "--batch-size"
    LOG_DIR = "--log-dir"
    FOLLOW = "--follow"
    TMDB = "--tmdb"
    ALL = "--all"


class CLICommands:
    """CLI command names."""

    SCAN = "scan"
    MATCH = "match"
    ORGANIZE = "organize"
    RUN = "run"
    LOG = "log"
    VERIFY = "verify"
    INIT = "init"


class CLIHelp:
    """CLI help text and descriptions."""

    VERSION_HELP = "Print version information and exit."
    VERSION_TEXT = "AniVault CLI v{version}"
    APP_NAME = "anivault"
    APP_DESCRIPTION = "AniVault - Advanced Anime Collection Management System"
    APP_STYLE: Literal["rich"] = "rich"
    MAIN_DESCRIPTION = """
    AniVault - Advanced Anime Collection Management System.

    A comprehensive tool for organizing anime collections with TMDB integration,
    intelligent file matching, and automated organization capabilities.
    """
    JSON_OUTPUT_HELP = "Output results in JSON format"
    SCAN_HELP = "Scan directory for anime files"
    SCAN_DIRECTORY_HELP = "Directory to scan for anime files"
    SCAN_RECURSIVE_HELP = "Scan directories recursively"
    SCAN_INCLUDE_SUBTITLES_HELP = "Include subtitle files in scan"
    SCAN_INCLUDE_METADATA_HELP = "Include metadata files in scan"
    SCAN_OUTPUT_HELP = "Output file for scan results (JSON format)"
    SCAN_JSON_HELP = JSON_OUTPUT_HELP
    MATCH_HELP = "Match anime files against TMDB database"
    MATCH_DIRECTORY_HELP = "Directory to match anime files against TMDB database"
    MATCH_RECURSIVE_HELP = "Match files recursively in subdirectories"
    MATCH_INCLUDE_SUBTITLES_HELP = "Include subtitle files in matching"
    MATCH_INCLUDE_METADATA_HELP = "Include metadata files in matching"
    MATCH_OUTPUT_HELP = "Output file for match results (JSON format)"
    MATCH_JSON_HELP = JSON_OUTPUT_HELP
    ORGANIZE_HELP = "Organize anime files into structured directories"
    ORGANIZE_DIRECTORY_HELP = "Directory containing scanned and matched anime files to organize"
    ORGANIZE_DRY_RUN_HELP = "Show what would be organized without actually moving files"
    ORGANIZE_YES_HELP = "Skip confirmation prompts and proceed with organization"
    ORGANIZE_JSON_HELP = JSON_OUTPUT_HELP
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
    RUN_HELP = "Run complete pipeline: scan, match, and organize"
    RUN_DIRECTORY_HELP = "Directory containing anime files to process"
    RUN_RECURSIVE_HELP = "Process files recursively in subdirectories"
    RUN_INCLUDE_SUBTITLES_HELP = "Include subtitle files in processing"
    RUN_INCLUDE_METADATA_HELP = "Include metadata files in processing"
    RUN_OUTPUT_HELP = "Output file for processing results (JSON format)"
    RUN_DRY_RUN_HELP = "Show what would be processed without actually processing files"
    RUN_YES_HELP = "Skip confirmation prompts and proceed with processing"
    RUN_JSON_HELP = JSON_OUTPUT_HELP
    LOG_HELP = "Manage operation logs"
    LOG_DIR_HELP = "Directory containing log files"
    VERIFY_HELP = "Verify system components and connectivity"
    VERIFY_TMDB_HELP = "Verify TMDB API connectivity"
    VERIFY_ALL_HELP = "Verify all components"


class CLIDefaults:
    """CLI default values."""

    VERSION = "0.1.0"
    DEFAULT_DESTINATION = "Anime"
    DEFAULT_VIDEO_EXTENSIONS: ClassVar[list[str]] = [
        "mp4",
        "mkv",
        "avi",
        "mov",
        "wmv",
        "flv",
        "webm",
        "m4v",
    ]
    DEFAULT_SIMILARITY_THRESHOLD = 0.8
    DEFAULT_MAX_WORKERS = 8
    DEFAULT_BATCH_SIZE = 50
    DEFAULT_YES = False
    DEFAULT_JSON = False
    DEFAULT_DRY_RUN = False
    DEFAULT_VERBOSE = 0
    DEFAULT_WORKER_COUNT = 4
    DEFAULT_CONCURRENCY_LIMIT = 4
    DEFAULT_SCAN_CONCURRENCY = 5
    DEFAULT_FILE_SIZE = 0
    EXIT_SUCCESS = 0
    EXIT_ERROR = 1
    HIGH_CONFIDENCE_THRESHOLD = 0.8
    MEDIUM_CONFIDENCE_THRESHOLD = 0.6
    LOW_CONFIDENCE_THRESHOLD = 0.0
    BYTES_PER_KB = 1024.0


class RunDefaults:
    """Run command default values."""

    DEFAULT_MAX_WORKERS = 4
    DEFAULT_BATCH_SIZE = 10
    DEFAULT_RATE_LIMIT = 50
    DEFAULT_CONCURRENT = 4
    DEFAULT_DESTINATION = "Anime"
    DEFAULT_EXTENSIONS: ClassVar[list[str]] = [
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


class LogCommands:
    """Log command subcommands."""

    LIST = "list"
    CLEAR = "clear"
    EXPORT = "export"
    SHOW = "show"


class DateFormats:
    """Date and time format constants."""

    STANDARD_DATETIME = "%Y-%m-%d %H:%M:%S"
    ISO_DATETIME = "%Y-%m-%dT%H:%M:%S"
    DATE_ONLY = "%Y-%m-%d"
    TIME_ONLY = "%H:%M:%S"
    FILENAME_SAFE = "%Y%m%d_%H%M%S"


class LogJsonKeys:
    """Log-specific JSON keys."""

    LOG_FILES = "log_files"
    FILE = "file"
    SIZE = "size"
    SIZE_BYTES = "size_bytes"
    MODIFIED = "modified"
    CREATED = "created"
    LOG_ENTRIES = "log_entries"
    LOG_LEVEL = "log_level"
    LOG_MESSAGE = "log_message"
    TIMESTAMP = "timestamp"
