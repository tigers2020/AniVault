"""Scan command handler for AniVault CLI.

Refactored to use decorator pattern for cleaner, more maintainable code.
Core logic moved to cli.helpers.scan module.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

import typer
from rich.console import Console as RichConsole

from anivault.cli.common.context import get_cli_context
from anivault.cli.common.error_decorator import handle_cli_errors
from anivault.cli.common.setup_decorator import setup_handler
from anivault.cli.helpers.scan import (
    _file_metadata_to_dict,
    collect_scan_data,
    display_scan_results,
    enrich_metadata,
    run_scan_pipeline,
)
from anivault.cli.json_formatter import format_json_output
from anivault.shared.constants import CLI, CLIDefaults, CLIFormatting
from anivault.shared.constants.cli import CLIHelp, CLIMessages, CLIOptions
from anivault.shared.constants.logging import LogConfig
from anivault.shared.metadata_models import FileMetadata
from anivault.shared.types.cli import CLIDirectoryPath, ScanOptions

logger = logging.getLogger(__name__)


@setup_handler(requires_directory=True, supports_json=True)
@handle_cli_errors(operation="handle_scan", command_name="scan")
def handle_scan_command(options: ScanOptions, **kwargs: Any) -> int:
    """Handle the scan command.

    Args:
        options: Validated scan command options
        **kwargs: Injected by decorators (console, logger_adapter)

    Returns:
        Exit code (0 for success, non-zero for error)
    """

    console = kwargs.get("console") or RichConsole()
    logger_adapter = kwargs.get("logger_adapter", logger)

    logger_adapter.info(
        CLI.INFO_COMMAND_STARTED.format(command=CLIMessages.CommandNames.SCAN)
    )

    # Extract Path from DirectoryPath or use directly
    directory = (
        options.directory.path
        if hasattr(options.directory, "path")
        else Path(str(options.directory))
    )

    # Check if JSON output is enabled
    context = get_cli_context()
    is_json_output = bool(context and context.is_json_output_enabled())

    # Run scan pipeline
    file_results = run_scan_pipeline(directory, console, is_json_output=is_json_output)

    # Handle empty results
    if not file_results:
        if is_json_output:
            # Return empty results in JSON format
            scan_data = collect_scan_data([], directory, show_tmdb=True)
            json_output = format_json_output(
                success=True,
                command="scan",
                data=scan_data,
                warnings=["No anime files found in the specified directory"],
            )
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            console.print(
                "[yellow]No anime files found in the specified directory[/yellow]"
            )
        return CLIDefaults.EXIT_SUCCESS

    # Enrich metadata if requested
    enrich_metadata_flag = True  # Default to enrich metadata
    if enrich_metadata_flag:
        enriched_results = asyncio.run(
            enrich_metadata(file_results, console, is_json_output=is_json_output)
        )
    else:
        enriched_results = file_results

    # Output results
    if is_json_output:
        # Collect scan statistics for JSON output
        # enriched_results is list[FileMetadata] from enrich_metadata
        scan_data = collect_scan_data(
            enriched_results, directory, show_tmdb=enrich_metadata_flag
        )

        # Output JSON to stdout
        json_output = format_json_output(
            success=True,
            command="scan",
            data=scan_data,
        )
        sys.stdout.buffer.write(json_output)
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
    else:
        # Display results in human-readable format
        # enriched_results is list[FileMetadata] from enrich_metadata
        display_scan_results(enriched_results, console, show_tmdb=enrich_metadata_flag)

        # Save results to file if requested
        if options.output:
            _save_results_to_file(enriched_results, options.output)

            console.print(
                CLIFormatting.format_colored_message(
                    CLI.SUCCESS_RESULTS_SAVED.format(path=options.output),
                    "success",
                )
            )

    logger_adapter.info(
        CLI.INFO_COMMAND_COMPLETED.format(command=CLIMessages.CommandNames.SCAN)
    )
    return CLIDefaults.EXIT_SUCCESS


def _save_results_to_file(results: list[FileMetadata], output_path: Path) -> None:
    """Save scan results to a JSON file.

    Args:
        results: List of FileMetadata instances
        output_path: Path to save the results
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert FileMetadata to JSON-serializable format
    json_results = []
    for metadata in results:
        json_result = _file_metadata_to_dict(metadata)
        json_results.append(json_result)

    with open(output_path, "w", encoding=LogConfig.DEFAULT_ENCODING) as f:
        json.dump(
            json_results,
            f,
            indent=CLI.INDENT_SIZE,
            ensure_ascii=False,
        )


def scan_command(
    directory: Path = typer.Argument(
        ...,
        help=CLIHelp.SCAN_DIRECTORY_HELP,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    recursive: bool = typer.Option(
        True,
        CLIOptions.RECURSIVE,
        CLIOptions.RECURSIVE_SHORT,
        help=CLIHelp.SCAN_RECURSIVE_HELP,
    ),
    include_subtitles: bool = typer.Option(
        True,
        CLIOptions.INCLUDE_SUBTITLES,
        help=CLIHelp.SCAN_INCLUDE_SUBTITLES_HELP,
    ),
    include_metadata: bool = typer.Option(
        True,
        CLIOptions.INCLUDE_METADATA,
        help=CLIHelp.SCAN_INCLUDE_METADATA_HELP,
    ),
    output_file: Path | None = typer.Option(
        None,
        CLIOptions.OUTPUT,
        CLIOptions.OUTPUT_SHORT,
        help=CLIHelp.SCAN_OUTPUT_HELP,
        writable=True,
    ),
    json: bool = typer.Option(
        False,
        CLIOptions.JSON,
        help=CLIHelp.SCAN_JSON_HELP,
    ),
) -> None:
    """Scan directories for anime files and extract metadata.

    This command recursively scans the specified directory for anime files
    and extracts metadata using anitopy. It can optionally include subtitle
    and metadata files in the scan results.

    The scan process includes:
    - File discovery based on supported extensions
    - Metadata extraction using anitopy parser
    - TMDB API enrichment for additional metadata
    - Progress tracking and error handling

    Supported file extensions: mkv, mp4, avi, mov, wmv, flv, webm, m4v
    Supported subtitle formats: srt, ass, ssa, vtt, smi, sub

    Examples:
        # Scan current directory with default settings
        anivault scan .

        # Scan specific directory with custom options
        anivault scan /path/to/anime --recursive --output results.json

        # Scan without subtitles (faster processing)
        anivault scan /path/to/anime --no-include-subtitles

        # Scan with verbose output for debugging
        anivault scan /path/to/anime --verbose

        # Save results to JSON file
        anivault scan /path/to/anime --output scan_results.json
    """
    try:
        # Validate arguments using Pydantic model
        scan_options = ScanOptions(
            directory=CLIDirectoryPath(path=directory),
            recursive=recursive,
            include_subtitles=include_subtitles,
            include_metadata=include_metadata,
            output=output_file,
            json_output=bool(json),
        )

        exit_code = handle_scan_command(scan_options)
        if exit_code != CLIDefaults.EXIT_SUCCESS:
            raise typer.Exit(exit_code)

    except ValueError as e:
        logger.exception("Validation error")
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(CLIDefaults.EXIT_ERROR) from e
