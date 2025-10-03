"""
CLI Argument Parser Module

This module handles all command-line argument parsing for AniVault CLI.
It separates the argument parsing logic from the main CLI module to follow
the Single Responsibility Principle.
"""

import argparse
import os
from pathlib import Path

from anivault.cli.common_options import get_common_options_parser, get_version_argument
from anivault.shared.constants import (
    CLI_DEFAULT_RATE_LIMIT_EXAMPLE,
    CLI_DEFAULT_RATE_LIMIT_HELP,
    CLI_DEFAULT_WORKERS_EXAMPLE,
    DEFAULT_CACHE_DIR,
    DEFAULT_CONCURRENT_REQUESTS,
    DEFAULT_RATE_LIMIT,
    DEFAULT_TMDB_RATE_LIMIT_RPS,
    DEFAULT_WORKERS,
    SUPPORTED_VIDEO_EXTENSIONS,
    SUPPORTED_VIDEO_EXTENSIONS_MATCH,
    SUPPORTED_VIDEO_EXTENSIONS_ORGANIZE,
)
from anivault.shared.errors import ApplicationError, ErrorCode


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure the main argument parser for AniVault CLI.

    Returns:
        argparse.ArgumentParser: Configured argument parser with all subcommands

    Raises:
        ApplicationError: If parser configuration fails
    """
    try:
        # Get common options parser for reuse across all commands
        common_options_parser = get_common_options_parser()

        parser = argparse.ArgumentParser(
            description=(
                "AniVault - Anime Collection Management System with TMDB Integration"
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

        return parser

    except Exception as e:
        raise ApplicationError(
            ErrorCode.CONFIGURATION_ERROR,
            f"Failed to create argument parser: {e}",
        ) from e


def parse_arguments(parser: argparse.ArgumentParser) -> argparse.Namespace:
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
  # Scan directory and enrich with TMDB metadata
  anivault scan /path/to/anime --enrich

  # Scan with custom settings
  anivault scan /path/to/anime --enrich --workers {CLI_DEFAULT_WORKERS_EXAMPLE} \\
    --rate-limit {CLI_DEFAULT_RATE_LIMIT_EXAMPLE}

  # Scan without TMDB enrichment (faster)
  anivault scan /path/to/anime --no-enrich
"""


# Global arguments are now handled by common_options.py
# This function is kept for backward compatibility but is no longer used
def _add_global_arguments(parser: argparse.ArgumentParser) -> None:
    """Add global arguments to the parser.

    DEPRECATED: This function is no longer used. Global arguments are now
    handled by the common_options.py module through parent parsers.
    """


def _add_scan_parser(subparsers) -> None:
    """Add scan command parser."""
    common_options_parser = get_common_options_parser()
    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan directory for anime files",
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
        help="Skip TMDB metadata enrichment",
    )

    scan_parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Number of worker threads (default: {DEFAULT_WORKERS})",
    )

    scan_parser.add_argument(
        "--rate-limit",
        type=float,
        default=DEFAULT_TMDB_RATE_LIMIT_RPS,
        help=(
            f"TMDB API rate limit in requests per second "
            f"(default: {CLI_DEFAULT_RATE_LIMIT_HELP})"
        ),
    )

    scan_parser.add_argument(
        "--concurrent",
        type=int,
        default=DEFAULT_CONCURRENT_REQUESTS,
        help=(
            f"Maximum concurrent TMDB requests "
            f"(default: {DEFAULT_CONCURRENT_REQUESTS})"
        ),
    )

    scan_parser.add_argument(
        "--extensions",
        nargs="+",
        default=list(SUPPORTED_VIDEO_EXTENSIONS),
        help=(
            f"File extensions to scan for "
            f"(default: {', '.join(SUPPORTED_VIDEO_EXTENSIONS)})"
        ),
    )

    scan_parser.add_argument(
        "--output",
        type=str,
        help="Output file for results (JSON format)",
    )


def _add_verify_parser(subparsers) -> None:
    """Add verify command parser."""
    common_options_parser = get_common_options_parser()
    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify system components",
        parents=[common_options_parser],
    )

    verify_parser.add_argument(
        "--tmdb",
        action="store_true",
        help="Verify TMDB API connectivity",
    )

    verify_parser.add_argument(
        "--all",
        action="store_true",
        help="Verify all components",
    )


def _add_match_parser(subparsers) -> None:
    """Add match command parser."""
    common_options_parser = get_common_options_parser()
    match_parser = subparsers.add_parser(
        "match",
        help="Match anime files with TMDB metadata using advanced matching engine",
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
        default=list(SUPPORTED_VIDEO_EXTENSIONS_MATCH),
        help=f"File extensions to process (default: {', '.join(SUPPORTED_VIDEO_EXTENSIONS_MATCH)})",
    )

    match_parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Number of concurrent workers (default: {DEFAULT_WORKERS})",
    )

    match_parser.add_argument(
        "--rate-limit",
        type=int,
        default=DEFAULT_RATE_LIMIT,
        help=f"TMDB API rate limit per minute (default: {DEFAULT_RATE_LIMIT})",
    )

    match_parser.add_argument(
        "--concurrent",
        type=int,
        default=DEFAULT_CONCURRENT_REQUESTS,
        help=f"Maximum concurrent TMDB API calls (default: {DEFAULT_CONCURRENT_REQUESTS})",
    )

    match_parser.add_argument(
        "--cache-dir",
        type=str,
        default=DEFAULT_CACHE_DIR,
        help=f"Cache directory for TMDB responses (default: {DEFAULT_CACHE_DIR})",
    )


def _add_organize_parser(subparsers) -> None:
    """Add organize command parser."""
    common_options_parser = get_common_options_parser()
    organize_parser = subparsers.add_parser(
        "organize",
        help="Organize anime files into structured directories with TMDB metadata",
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
        default=list(SUPPORTED_VIDEO_EXTENSIONS_ORGANIZE),
        help=f"File extensions to process (default: {', '.join(SUPPORTED_VIDEO_EXTENSIONS_ORGANIZE)})",
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


def _add_log_parser(subparsers) -> None:
    """Add log command parser."""
    common_options_parser = get_common_options_parser()
    log_parser = subparsers.add_parser(
        "log",
        help="Manage operation logs for tracking and rollback purposes",
        parents=[common_options_parser],
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


def _add_rollback_parser(subparsers) -> None:
    """Add rollback command parser."""
    common_options_parser = get_common_options_parser()
    rollback_parser = subparsers.add_parser(
        "rollback",
        help="Revert a previous organization operation using an operation log",
        parents=[common_options_parser],
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


def _add_run_parser(subparsers) -> None:
    """Add run command parser."""
    common_options_parser = get_common_options_parser()
    run_parser = subparsers.add_parser(
        "run",
        help="Run the complete anime organization workflow (scan, match, organize) in sequence",
        parents=[common_options_parser],
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
        help="Skip the scan step and use existing scan results",
    )

    run_parser.add_argument(
        "--skip-match",
        action="store_true",
        help="Skip the match step and use existing match results",
    )

    run_parser.add_argument(
        "--skip-organize",
        action="store_true",
        help="Skip the organize step and only perform scan and match",
    )

    run_parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Maximum number of worker threads for parallel processing (default: 4)",
    )

    run_parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of files to process in each batch (default: 100)",
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
