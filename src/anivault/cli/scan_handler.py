"""Scan command handler for AniVault CLI.

Orchestration entry point: Container → ScanUseCase → MetadataEnricher → helper (format only).
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import typer
from dependency_injector.wiring import Provide, inject
from rich.console import Console as RichConsole

from anivault.cli.common.context import get_cli_context
from anivault.cli.common.error_decorator import handle_cli_errors
from anivault.cli.common.setup_decorator import setup_handler
from anivault.cli.helpers.scan import (
    _file_metadata_to_dict,
    collect_scan_data,
    display_scan_results,
)
from anivault.cli.json_formatter import format_json_output
from anivault.cli.progress import create_progress_manager
from anivault.containers import Container
from anivault.core.parser.models import ParsingAdditionalInfo, ParsingResult
from anivault.services.enricher import MetadataEnricher
from anivault.services.enricher.metadata_enricher.models import EnrichedMetadata
from anivault.shared.constants import CLI, CLIDefaults, CLIFormatting
from anivault.shared.constants.cli import CLIHelp, CLIMessages, CLIOptions
from anivault.shared.constants.file_formats import VideoFormats
from anivault.shared.constants.logging import LogConfig
from anivault.shared.constants.scan_fields import ScanMessages
from anivault.shared.constants import QueueConfig
from anivault.shared.models.metadata import FileMetadata
from anivault.shared.types.cli import CLIDirectoryPath, ScanOptions
from anivault.app.use_cases.scan_use_case import ScanUseCase

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Private pipeline helpers (handler-internal, keeps handle_scan_command thin)
# ---------------------------------------------------------------------------

@inject
def _run_scan(
    directory: Path,
    *,
    is_json_output: bool = False,
    scan_use_case: ScanUseCase = Provide[Container.scan_use_case],
) -> list[FileMetadata]:
    """Execute scan UseCase and return raw FileMetadata list.

    Args:
        directory: Directory to scan
        is_json_output: Whether JSON output is enabled (suppresses progress)
        scan_use_case: Injected ScanUseCase from Container

    Returns:
        List of FileMetadata from scanner
    """
    progress_manager = create_progress_manager(disabled=is_json_output)
    with progress_manager.spinner("Scanning files..."):
        return scan_use_case.execute(
            directory=directory,
            extensions=list(VideoFormats.ALL_EXTENSIONS),
            num_workers=CLIDefaults.DEFAULT_WORKER_COUNT,
            max_queue_size=QueueConfig.DEFAULT_SIZE,
        )


def _file_metadata_to_parsing_result(metadata: FileMetadata) -> ParsingResult:
    """Convert FileMetadata to ParsingResult for enrichment."""
    return ParsingResult(
        title=metadata.title,
        episode=metadata.episode,
        season=metadata.season,
        year=metadata.year,
        quality=None,
        source=None,
        codec=None,
        audio=None,
        release_group=None,
        confidence=1.0,
        parser_used="file_metadata_converter",
        additional_info=ParsingAdditionalInfo(),
    )


@inject
async def _enrich_results(
    file_results: list[FileMetadata],
    *,
    is_json_output: bool = False,
    enricher: MetadataEnricher = Provide[Container.metadata_enricher],
) -> list[FileMetadata]:
    """Enrich FileMetadata list with TMDB data via MetadataEnricher.

    Args:
        file_results: Raw scan results to enrich
        is_json_output: Whether JSON output is enabled (suppresses progress)
        enricher: Injected MetadataEnricher from Container

    Returns:
        List of enriched FileMetadata
    """
    if not file_results:
        return file_results

    progress_manager = create_progress_manager(disabled=is_json_output)
    parsing_results = [_file_metadata_to_parsing_result(m) for m in file_results]

    enriched_list: list[EnrichedMetadata] = []
    for pr in progress_manager.track(parsing_results, "Enriching metadata..."):
        enriched = await enricher.enrich_metadata(pr)
        enriched_list.append(enriched)

    return [
        enriched.to_file_metadata(original.file_path)
        for original, enriched in zip(file_results, enriched_list)
    ]


def _emit_scan_output(
    results: list[FileMetadata],
    directory: Path,
    *,
    is_json_output: bool,
    console: RichConsole,
) -> None:
    """Emit scan results to JSON stdout or rich TTY table.

    Args:
        results: Enriched FileMetadata list
        directory: Scanned directory (for JSON summary)
        is_json_output: Output mode switch
        console: Rich console
    """
    import sys

    if is_json_output:
        scan_data = collect_scan_data(results, directory, show_tmdb=True)
        json_output = format_json_output(
            success=True,
            command="scan",
            data=scan_data,
        )
        sys.stdout.buffer.write(json_output)
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
    else:
        display_scan_results(results, console, show_tmdb=True)
        if results:
            console.print(
                CLIFormatting.format_colored_message(
                    ScanMessages.SCAN_COMPLETED,
                    "success",
                )
            )


def _save_results_to_file(results: list[FileMetadata], output_path: Path) -> None:
    """Save enriched scan results to a JSON file.

    Args:
        results: Enriched FileMetadata list
        output_path: Destination path
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    json_results = [_file_metadata_to_dict(m) for m in results]
    with open(output_path, "w", encoding=LogConfig.DEFAULT_ENCODING) as f:
        json.dump(json_results, f, indent=CLI.INDENT_SIZE, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Command entry point
# ---------------------------------------------------------------------------


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
    import sys

    console = kwargs.get("console") or RichConsole()
    logger_adapter = kwargs.get("logger_adapter", logger)

    logger_adapter.info(CLI.INFO_COMMAND_STARTED.format(command=CLIMessages.CommandNames.SCAN))

    directory = options.directory.path if hasattr(options.directory, "path") else Path(str(options.directory))
    context = get_cli_context()
    is_json_output = bool(context and context.is_json_output_enabled())

    # 1. Scan
    file_results = _run_scan(directory, is_json_output=is_json_output)

    if not file_results:
        if is_json_output:
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
            console.print("[yellow]No anime files found in the specified directory[/yellow]")
        return CLIDefaults.EXIT_SUCCESS

    # 2. Enrich
    enriched_results = asyncio.run(_enrich_results(file_results, is_json_output=is_json_output))

    # 3. Output
    _emit_scan_output(enriched_results, directory, is_json_output=is_json_output, console=console)

    # 4. Optionally save to file
    if not is_json_output and options.output:
        _save_results_to_file(enriched_results, options.output)
        console.print(
            CLIFormatting.format_colored_message(
                CLI.SUCCESS_RESULTS_SAVED.format(path=options.output),
                "success",
            )
        )

    logger_adapter.info(CLI.INFO_COMMAND_COMPLETED.format(command=CLIMessages.CommandNames.SCAN))
    return CLIDefaults.EXIT_SUCCESS


def scan_command(  # pylint: disable=too-many-arguments,too-many-positional-arguments
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
    json: bool = typer.Option(  # pylint: disable=redefined-outer-name
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
