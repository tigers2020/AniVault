"""
CLI Argument Parser Module

This module handles all command-line argument parsing for AniVault CLI.
It separates the argument parsing logic from the main CLI module to follow
the Single Responsibility Principle.
"""

import argparse
import os
from pathlib import Path
from typing import Any

from anivault.cli.common_options import get_common_options_parser, get_version_argument
from anivault.cli_utils import ConfigAwareArgumentParser
from anivault.shared.constants import (
    APIConfig,
    CLIFormatting,
    TMDBConfig,
    VideoFormats,
    WorkerConfig,
)
from anivault.shared.constants import (
    CLICacheConfig as CacheConfig,
)
from anivault.shared.errors import ApplicationError, ErrorCode


def create_argument_parser() -> ConfigAwareArgumentParser:
    """
    Create and configure the main argument parser for AniVault CLI.

    Returns:
        ConfigAwareArgumentParser: Configured argument parser with all subcommands

    Raises:
        ApplicationError: If parser configuration fails
    """
    try:
        # Get common options parser for reuse across all commands
        common_options_parser = get_common_options_parser()

        parser = ConfigAwareArgumentParser(
            description=(
                "AniVault - Advanced Anime Collection Management System\n"
                "\n"
                "A comprehensive tool for organizing anime collections with TMDB integration, "
                "intelligent file matching, and automated organization capabilities. "
                "AniVault helps you scan, identify, and organize your anime files into "
                "structured directories with proper metadata enrichment."
            ),
            prog="anivault",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=_get_help_epilog(),
            parents=[common_options_parser],  # Integrate common options
        )

        # Add version argument to main parser only
        version_config = get_version_argument()
        parser.add_argument("--version", **version_config)

        # Subcommands
        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # Add all subcommand parsers
        _add_scan_parser(subparsers)
        _add_verify_parser(subparsers)
        _add_match_parser(subparsers)
        _add_organize_parser(subparsers)
        _add_log_parser(subparsers)
        _add_rollback_parser(subparsers)
        _add_run_parser(subparsers)
        _add_legacy_verification_flags(parser)

        # Load configuration for dynamic defaults
        parser.load_config()

        return parser

    except Exception as e:
        raise ApplicationError(
            ErrorCode.CONFIGURATION_ERROR,
            f"Failed to create argument parser: {e}",
        ) from e


def parse_arguments(parser: ConfigAwareArgumentParser) -> argparse.Namespace:
    """
    Parse command line arguments using the provided parser.

    Args:
        parser: Configured argument parser

    Returns:
        argparse.Namespace: Parsed arguments

    Raises:
        ApplicationError: If argument parsing fails
    """
    try:
        args = parser.parse_args()

        # Apply configuration defaults if parser has loaded config
        if parser._config_loaded and parser._config_manager:
            from anivault.cli_utils import apply_config_defaults, create_config_mappings

            config_mappings = create_config_mappings()
            apply_config_defaults(args, parser._config_manager, config_mappings)

        validate_parsed_args(args)
        return args

    except SystemExit as e:
        # argparse calls sys.exit() on help/version, we need to handle this
        if e.code == 0:
            # Help or version was requested, this is normal
            raise SystemExit(0) from None
        # Invalid arguments
        raise ApplicationError(
            ErrorCode.CLI_INVALID_ARGUMENTS,
            "Invalid command line arguments",
        ) from e
    except Exception as e:
        raise ApplicationError(
            ErrorCode.CLI_INVALID_ARGUMENTS,
            f"Failed to parse arguments: {e}",
        ) from e


def validate_parsed_args(args: argparse.Namespace) -> None:
    """
    Validate parsed arguments for logical consistency and requirements.

    Args:
        args: Parsed command line arguments

    Raises:
        ApplicationError: If validation fails
    """
    try:
        # Validate directory arguments
        if hasattr(args, "directory") and args.directory:
            validate_directory_path(args.directory)

        # Validate numeric ranges
        if hasattr(args, "workers") and args.workers:
            if args.workers < 1 or args.workers > 32:
                raise ApplicationError(
                    ErrorCode.CLI_INVALID_ARGUMENTS,
                    "Workers must be between 1 and 32",
                )

        if hasattr(args, "rate_limit") and args.rate_limit:
            if args.rate_limit <= 0 or args.rate_limit > 100:
                raise ApplicationError(
                    ErrorCode.CLI_INVALID_ARGUMENTS,
                    "Rate limit must be between 0.1 and 100 requests per second",
                )

        if hasattr(args, "concurrent") and args.concurrent:
            if args.concurrent < 1 or args.concurrent > 20:
                raise ApplicationError(
                    ErrorCode.CLI_INVALID_ARGUMENTS,
                    "Concurrent requests must be between 1 and 20",
                )

        # Validate file extensions
        if hasattr(args, "extensions") and args.extensions:
            validate_file_extensions(args.extensions)

        # Note: enrich/no-enrich mutual exclusivity is handled by
        # argparse mutually_exclusive_group

    except ApplicationError:
        raise
    except Exception as e:
        raise ApplicationError(
            ErrorCode.VALIDATION_ERROR,
            f"Argument validation failed: {e}",
        ) from e


def validate_directory_path(directory_path: str) -> None:
    """
    Validate that a directory path exists and is accessible.

    Args:
        directory_path: Path to validate

    Raises:
        ApplicationError: If directory is invalid
    """
    try:
        path = Path(directory_path)

        if not path.exists():
            raise ApplicationError(
                ErrorCode.DIRECTORY_NOT_FOUND,
                f"Directory '{directory_path}' does not exist",
            )

        if not path.is_dir():
            raise ApplicationError(
                ErrorCode.INVALID_PATH,
                f"'{directory_path}' is not a directory",
            )

        # Check read permissions
        if not os.access(path, os.R_OK):
            raise ApplicationError(
                ErrorCode.PERMISSION_DENIED,
                f"No read permission for directory '{directory_path}'",
            )

    except ApplicationError:
        raise
    except Exception as e:
        raise ApplicationError(
            ErrorCode.VALIDATION_ERROR,
            f"Directory validation failed: {e}",
        ) from e


def validate_file_extensions(extensions: list[str]) -> None:
    """
    Validate file extensions format.

    Args:
        extensions: List of file extensions to validate

    Raises:
        ApplicationError: If extensions are invalid
    """
    try:
        for ext in extensions:
            if not ext.startswith("."):
                raise ApplicationError(
                    ErrorCode.CLI_INVALID_ARGUMENTS,
                    f"File extension '{ext}' must start with a dot",
                )

            if len(ext) < 2:
                raise ApplicationError(
                    ErrorCode.CLI_INVALID_ARGUMENTS,
                    f"File extension '{ext}' is too short",
                )

    except ApplicationError:
        raise
    except Exception as e:
        raise ApplicationError(
            ErrorCode.VALIDATION_ERROR,
            f"Extension validation failed: {e}",
        ) from e


def _get_help_epilog() -> str:
    """Get the help epilog text with examples."""
    return f"""
Examples:
  # Basic workflow - scan, match, and organize in one command
  anivault run /path/to/anime --dry-run

  # Scan directory and enrich with TMDB metadata
  anivault scan /path/to/anime --enrich

  # Scan with custom performance settings
  anivault scan /path/to/anime --enrich --workers {CLIFormatting.DEFAULT_WORKERS_EXAMPLE} \\
    --rate-limit {CLIFormatting.DEFAULT_RATE_LIMIT_EXAMPLE}

  # Match files with TMDB metadata
  anivault match /path/to/anime --workers 4

  # Organize files with dry-run preview
  anivault organize /path/to/anime --dry-run

  # View operation logs
  anivault log list

  # Rollback a previous organization
  anivault rollback 2024-01-15_14-30-25

  # Verify system components
  anivault verify --all

  # Use JSON output for scripting
  anivault scan /path/to/anime --json > results.json

For more information about a specific command, use:
  anivault <command> --help
"""


# Global arguments are now handled by common_options.py
# This function is kept for backward compatibility but is no longer used
def _add_global_arguments(parser: argparse.ArgumentParser) -> None:
    """Add global arguments to the parser.

    DEPRECATED: This function is no longer used. Global arguments are now
    handled by the common_options.py module through parent parsers.
    """


def _add_scan_parser(subparsers: Any) -> None:
    """Add scan command parser."""
    common_options_parser = get_common_options_parser()
    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan directory for anime files and optionally enrich with TMDB metadata",
        description=(
            "Scan a directory for anime files and extract metadata from filenames. "
            "Optionally enrich the metadata by querying TMDB API for additional "
            "information like series titles, episode numbers, and air dates. "
            "This is the first step in the anime organization workflow."
        ),
        epilog="""
Examples:
  # Basic scan with TMDB enrichment (recommended)
  anivault scan /path/to/anime --enrich

  # Fast scan without TMDB API calls
  anivault scan /path/to/anime --no-enrich

  # High-performance scan with custom settings
  anivault scan /path/to/anime --enrich --workers 8 --rate-limit 20

  # Scan specific file types only
  anivault scan /path/to/anime --extensions .mkv .mp4 --enrich

  # Save results to file
  anivault scan /path/to/anime --enrich --output results.json

  # Use JSON output for scripting
  anivault scan /path/to/anime --json --enrich > scan_results.json
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common_options_parser],
    )

    scan_parser.add_argument(
        "directory",
        type=str,
        help="Directory to scan for anime files",
    )

    enrich_group = scan_parser.add_mutually_exclusive_group()
    enrich_group.add_argument(
        "--enrich",
        action="store_true",
        help="Enrich metadata with TMDB data (default behavior)",
    )

    enrich_group.add_argument(
        "--no-enrich",
        action="store_true",
        help="Skip TMDB metadata enrichment for faster scanning",
    )

    scan_parser.add_argument(
        "--workers",
        type=int,
        default=WorkerConfig.DEFAULT,
        help=f"Number of worker threads for parallel processing (default: {WorkerConfig.DEFAULT})",
    )

    scan_parser.add_argument(
        "--rate-limit",
        type=float,
        default=TMDBConfig.RATE_LIMIT_RPS,
        help=(
            f"TMDB API rate limit in requests per second "
            f"(default: {CLIFormatting.DEFAULT_RATE_LIMIT_HELP})"
        ),
    )

    scan_parser.add_argument(
        "--concurrent",
        type=int,
        default=APIConfig.DEFAULT_CONCURRENT_REQUESTS,
        help=(
            f"Maximum concurrent TMDB API requests "
            f"(default: {APIConfig.DEFAULT_CONCURRENT_REQUESTS})"
        ),
    )

    scan_parser.add_argument(
        "--extensions",
        nargs="+",
        default=list(VideoFormats.ALL_EXTENSIONS),
        help=(
            f"File extensions to scan for "
            f"(default: {', '.join(VideoFormats.ALL_EXTENSIONS)})"
        ),
    )

    scan_parser.add_argument(
        "--output",
        type=str,
        help="Output file for scan results (JSON format)",
    )


def _add_verify_parser(subparsers: Any) -> None:
    """Add verify command parser."""
    common_options_parser = get_common_options_parser()
    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify system components and dependencies",
        description=(
            "Verify that all system components and dependencies are working correctly. "
            "This includes checking TMDB API connectivity, validating required libraries, "
            "and ensuring the system is properly configured for anime file processing."
        ),
        epilog="""
Examples:
  # Verify all system components
  anivault verify --all

  # Check only TMDB API connectivity
  anivault verify --tmdb

  # Basic verification (checks core components)
  anivault verify

  # Use JSON output for automated testing
  anivault verify --all --json
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common_options_parser],
    )

    verify_parser.add_argument(
        "--tmdb",
        action="store_true",
        help="Verify TMDB API connectivity and authentication",
    )

    verify_parser.add_argument(
        "--all",
        action="store_true",
        help="Verify all system components including dependencies and API connectivity",
    )


def _add_match_parser(subparsers: Any) -> None:
    """Add match command parser."""
    common_options_parser = get_common_options_parser()
    match_parser = subparsers.add_parser(
        "match",
        help="Match anime files with TMDB metadata using advanced matching engine",
        description=(
            "Match anime files with TMDB metadata using intelligent filename parsing "
            "and fuzzy matching algorithms. This command analyzes anime filenames, "
            "extracts series information, and matches them against TMDB database to "
            "provide accurate metadata for organization."
        ),
        epilog="""
Examples:
  # Basic matching with default settings
  anivault match /path/to/anime

  # High-performance matching with custom workers
  anivault match /path/to/anime --workers 8 --concurrent 6

  # Match specific file types only
  anivault match /path/to/anime --extensions .mkv .mp4

  # Use custom cache directory
  anivault match /path/to/anime --cache-dir /custom/cache

  # Adjust API rate limiting for slower connections
  anivault match /path/to/anime --rate-limit 10

  # Use JSON output for scripting
  anivault match /path/to/anime --json > match_results.json
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common_options_parser],
    )

    match_parser.add_argument(
        "directory",
        type=str,
        help="Directory to scan for anime files",
    )

    match_parser.add_argument(
        "--extensions",
        nargs="+",
        default=list(VideoFormats.MATCH_EXTENSIONS),
        help=f"File extensions to process (default: {', '.join(VideoFormats.MATCH_EXTENSIONS)})",
    )

    match_parser.add_argument(
        "--workers",
        type=int,
        default=WorkerConfig.DEFAULT,
        help=f"Number of concurrent workers for parallel processing (default: {WorkerConfig.DEFAULT})",
    )

    match_parser.add_argument(
        "--rate-limit",
        type=int,
        default=APIConfig.DEFAULT_RATE_LIMIT,
        help=f"TMDB API rate limit per minute (default: {APIConfig.DEFAULT_RATE_LIMIT})",
    )

    match_parser.add_argument(
        "--concurrent",
        type=int,
        default=APIConfig.DEFAULT_CONCURRENT_REQUESTS,
        help=f"Maximum concurrent TMDB API calls (default: {APIConfig.DEFAULT_CONCURRENT_REQUESTS})",
    )

    match_parser.add_argument(
        "--cache-dir",
        type=str,
        default=CacheConfig.DEFAULT_DIR,
        help=f"Cache directory for TMDB responses (default: {CacheConfig.DEFAULT_DIR})",
    )


def _add_organize_parser(subparsers: Any) -> None:
    """Add organize command parser."""
    common_options_parser = get_common_options_parser()
    organize_parser = subparsers.add_parser(
        "organize",
        help="Organize anime files into structured directories with TMDB metadata",
        description=(
            "Organize anime files into structured directories based on TMDB metadata. "
            "This command creates organized folder structures using series names, "
            "seasons, and episode information. It supports dry-run mode for safe "
            "previewing and includes rollback capabilities for easy recovery."
        ),
        epilog="""
Examples:
  # Preview organization plan (recommended first step)
  anivault organize /path/to/anime --dry-run

  # Execute organization with confirmation
  anivault organize /path/to/anime

  # Skip confirmation and organize immediately
  anivault organize /path/to/anime --yes

  # Organize specific file types only
  anivault organize /path/to/anime --extensions .mkv .mp4 --dry-run

  # Organize to a different output directory
  anivault organize /path/to/anime --output-dir /organized/anime --dry-run

  # Use JSON output for automation
  anivault organize /path/to/anime --json --dry-run > organize_plan.json

  # Combine with other options
  anivault organize /path/to/anime --extensions .mkv --output-dir /organized --yes
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common_options_parser],
    )

    organize_parser.add_argument(
        "directory",
        type=str,
        help="Directory containing anime files to organize",
    )

    organize_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview planned file operations without making any changes to the filesystem",
    )

    organize_parser.add_argument(
        "--extensions",
        nargs="+",
        default=list(VideoFormats.ORGANIZE_EXTENSIONS),
        help=f"File extensions to process (default: {', '.join(VideoFormats.ORGANIZE_EXTENSIONS)})",
    )

    organize_parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory for organized files (default: same as input directory)",
    )

    organize_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip the confirmation prompt and execute the organization plan immediately",
    )

    # Enhanced organization options
    organize_parser.add_argument(
        "--enhanced",
        action="store_true",
        help="Enable enhanced organization with file grouping, Korean titles, and resolution-based sorting",
    )

    organize_parser.add_argument(
        "--destination",
        type=str,
        default="Anime",
        help="Base destination directory for organized files (default: Anime)",
    )

    organize_parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.7,
        help="Similarity threshold for file grouping (0.0 to 1.0, default: 0.7)",
    )


def _add_log_parser(subparsers: Any) -> None:
    """Add log command parser."""
    common_options_parser = get_common_options_parser()
    log_parser = subparsers.add_parser(
        "log",
        description="""Manage operation logs for tracking and rollback purposes.
AniVault automatically creates detailed logs for each organization operation,
including file movements, directory creation, and metadata changes. These logs
enable you to track what was done and easily rollback changes if needed.
""",
        help="Manage operation logs for tracking and rollback purposes",
        parents=[common_options_parser],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all available operation logs
  anivault log list

  # List logs from a specific directory
  anivault log list --log-dir /custom/logs

  # Use JSON output for scripting
  anivault log list --json

  # View logs with verbose output
  anivault log list --verbose

For more information about rollback operations, use:
  anivault rollback --help
""",
    )

    log_subparsers = log_parser.add_subparsers(
        dest="log_command",
        help="Available log management commands",
    )

    # Log list command
    log_list_parser = log_subparsers.add_parser(
        "list",
        help="Display all available operation logs from previous organize commands",
        parents=[common_options_parser],
    )
    log_list_parser.add_argument(
        "--log-dir",
        type=str,
        default="logs",
        help="Directory containing log files (default: logs)",
    )


def _add_rollback_parser(subparsers: Any) -> None:
    """Add rollback command parser."""
    common_options_parser = get_common_options_parser()
    rollback_parser = subparsers.add_parser(
        "rollback",
        description="""Revert a previous organization operation using an operation log.
This command allows you to undo file movements and directory changes made during
a previous organization operation. It uses the detailed logs created by AniVault
to restore your files to their original locations and remove created directories.

Use 'anivault log list' to see available operation logs and their timestamps.
Always use --dry-run first to preview what will be reverted.
""",
        help="Revert a previous organization operation using an operation log",
        parents=[common_options_parser],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview rollback operations (recommended first step)
  anivault rollback 2024-01-15_14-30-25 --dry-run

  # Execute rollback with confirmation
  anivault rollback 2024-01-15_14-30-25

  # Skip confirmation and rollback immediately
  anivault rollback 2024-01-15_14-30-25 --yes

  # Use JSON output for automation
  anivault rollback 2024-01-15_14-30-25 --json --dry-run

  # View available logs first
  anivault log list

Workflow:
  1. Use 'anivault log list' to see available operation logs
  2. Copy the timestamp (log ID) from the desired operation
  3. Use 'anivault rollback <log_id> --dry-run' to preview changes
  4. Use 'anivault rollback <log_id>' to execute the rollback

For more information about available logs, use:
  anivault log --help
""",
    )

    rollback_parser.add_argument(
        "log_id",
        type=str,
        help="The log ID (timestamp) from 'log list' to use for the rollback operation",
    )

    rollback_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview planned rollback operations without making any changes to the filesystem",
    )

    rollback_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip the confirmation prompt and execute the rollback immediately",
    )


def _add_run_parser(subparsers: Any) -> None:
    """Add run command parser."""
    common_options_parser = get_common_options_parser()
    run_parser = subparsers.add_parser(
        "run",
        description="""Execute the complete anime organization workflow in a single command.
This is the most convenient way to process anime files, combining scan, match,
and organize operations into one streamlined process. Perfect for users who
want to organize their entire anime collection with minimal interaction.

The run command performs these steps in sequence:
1. Scan: Discover anime files and extract metadata from filenames
2. Match: Query TMDB API to enrich metadata with series information
3. Organize: Create structured directories and move files accordingly

Use --dry-run to preview operations before making any changes.
""",
        help="Execute complete anime organization workflow (scan, match, organize)",
        parents=[common_options_parser],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Complete workflow with dry-run preview (recommended first step)
  anivault run /path/to/anime --dry-run

  # Execute complete organization workflow
  anivault run /path/to/anime

  # Skip confirmation prompts for automation
  anivault run /path/to/anime --yes

  # Process only specific file types
  anivault run /path/to/anime --extensions .mkv .mp4 --dry-run

  # Skip certain steps (useful for debugging or partial runs)
  anivault run /path/to/anime --skip-scan --skip-match  # Only organize
  anivault run /path/to/anime --skip-organize           # Only scan and match

  # High-performance processing with custom settings
  anivault run /path/to/anime --max-workers 8 --batch-size 200

  # Use JSON output for automation and scripting
  anivault run /path/to/anime --json --yes > organization_results.json

  # Combine multiple options for advanced workflows
  anivault run /path/to/anime --extensions .mkv --max-workers 6 --batch-size 150 --dry-run

Workflow Steps:
  The run command combines three individual commands:
  • anivault scan    - Discover and parse anime files
  • anivault match   - Enrich with TMDB metadata
  • anivault organize - Create organized directory structure

For more control over individual steps, use the separate scan, match, and organize commands.
""",
    )

    run_parser.add_argument(
        "directory",
        type=str,
        help="Directory to scan for anime files",
    )

    run_parser.add_argument(
        "--extensions",
        nargs="+",
        default=[".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"],
        help="File extensions to include in the scan (default: .mkv .mp4 .avi .mov .wmv .flv .webm .m4v)",
    )

    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview planned operations without making any changes to the filesystem",
    )

    run_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompts and execute operations immediately",
    )

    run_parser.add_argument(
        "--skip-scan",
        action="store_true",
        help="Skip the scan step and use existing scan results (useful for resuming interrupted workflows)",
    )

    run_parser.add_argument(
        "--skip-match",
        action="store_true",
        help="Skip the match step and use existing match results (useful for resuming interrupted workflows)",
    )

    run_parser.add_argument(
        "--skip-organize",
        action="store_true",
        help="Skip the organize step and only perform scan and match (useful for testing or partial workflows)",
    )

    run_parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Maximum number of worker threads for parallel processing (default: 4, recommended: 4-8)",
    )

    run_parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of files to process in each batch (default: 100, larger batches = more memory usage)",
    )


def _add_legacy_verification_flags(parser: argparse.ArgumentParser) -> None:
    """Add legacy verification flags."""
    verification_group = parser.add_argument_group("Legacy Verification Flags")

    verification_group.add_argument(
        "--verify-anitopy",
        action="store_true",
        help="Verify anitopy functionality in bundled executable",
    )

    verification_group.add_argument(
        "--verify-crypto",
        action="store_true",
        help="Verify cryptography functionality in bundled executable",
    )

    verification_group.add_argument(
        "--verify-tmdb",
        action="store_true",
        help="Verify tmdbv3api functionality in bundled executable",
    )

    verification_group.add_argument(
        "--verify-rich",
        action="store_true",
        help="Verify rich console rendering in bundled executable",
    )

    verification_group.add_argument(
        "--verify-prompt",
        action="store_true",
        help="Verify prompt_toolkit functionality in bundled executable",
    )
