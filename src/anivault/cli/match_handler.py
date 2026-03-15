"""Match command handler for AniVault CLI.

Orchestration entry point: Container → MatchUseCase → helper (format only).
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

import typer
from dependency_injector.wiring import Provide, inject
from rich.console import Console

from anivault.app.use_cases.match_use_case import MatchUseCase
from anivault.cli.common.context import get_cli_context
from anivault.cli.common.error_decorator import handle_cli_errors
from anivault.cli.common.path_utils import extract_directory_path
from anivault.cli.common.setup_decorator import setup_handler
from anivault.cli.helpers.match import output_match_results
from anivault.cli.helpers.match_formatters import collect_match_data
from anivault.cli.json_formatter import format_json_output
from anivault.cli.progress import create_progress_manager
from anivault.containers import Container
from anivault.shared.constants import CLI
from anivault.shared.constants.cli import CLIFormatting, CLIMessages
from anivault.shared.constants.system import FileSystem
from anivault.shared.types.cli import CLIDirectoryPath as DirectoryPath, MatchOptions

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Private pipeline helpers
# ---------------------------------------------------------------------------


@inject
async def _execute_match(
    directory: Path,
    options: MatchOptions,
    console: Console,
    *,
    use_case: MatchUseCase = Provide[Container.match_use_case],
) -> list:
    """Run MatchUseCase and return processed results.

    Args:
        directory: Directory to match files in
        options: Match command options
        console: Rich console for progress output
        use_case: Injected MatchUseCase from Container

    Returns:
        List of FileMetadata results
    """
    if not options.json_output:
        console.print(
            CLIFormatting.format_colored_message(
                f"Matching anime files in: {directory}",
                "success",
            )
        )

    progress_manager = create_progress_manager(disabled=options.json_output)
    with progress_manager.spinner(CLIMessages.Info.SCANNING_FILES):
        return await use_case.execute(
            directory,
            extensions=tuple(FileSystem.CLI_VIDEO_EXTENSIONS),
            concurrency=4,
        )


# ---------------------------------------------------------------------------
# Command entry point
# ---------------------------------------------------------------------------


@setup_handler(requires_directory=True, supports_json=True)
@handle_cli_errors(operation="handle_match", command_name="match")
def handle_match_command(options: MatchOptions, **kwargs: Any) -> int:
    """Handle the match command.

    Args:
        options: Validated match command options
        **kwargs: Injected by decorators (console, logger_adapter)

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    console = kwargs.get("console") or Console()
    logger_adapter = kwargs.get("logger_adapter", logger)

    logger_adapter.info(CLI.INFO_COMMAND_STARTED.format(command=CLIMessages.CommandNames.MATCH))

    directory = extract_directory_path(options.directory)

    processed_results = asyncio.run(_execute_match(directory, options, console))

    if not processed_results:
        if options.json_output:
            match_data = collect_match_data([], str(directory))
            json_output = format_json_output(
                success=True,
                command=CLIMessages.CommandNames.MATCH,
                data=match_data,
                warnings=[CLIMessages.Info.NO_ANIME_FILES_FOUND],
            )
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            console.print(
                CLIFormatting.format_colored_message(
                    CLIMessages.Info.NO_ANIME_FILES_FOUND,
                    "warning",
                )
            )
        return 0

    if not options.json_output:
        console.print(
            CLIFormatting.format_colored_message(
                f"Found {len(processed_results)} anime files",
                "info",
            )
        )

    output_match_results(processed_results, str(directory), options, console)

    logger_adapter.info(CLI.INFO_COMMAND_COMPLETED.format(command=CLIMessages.CommandNames.MATCH))
    return 0


def match_command(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    directory: Path = typer.Argument(
        ...,
        help="Directory to match anime files against TMDB database",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    recursive: bool = typer.Option(
        True,
        "--recursive/--no-recursive",
        "-r",
        help="Match files recursively in subdirectories",
    ),
    include_subtitles: bool = typer.Option(
        True,
        "--include-subtitles/--no-include-subtitles",
        help="Include subtitle files in matching",
    ),
    include_metadata: bool = typer.Option(
        True,
        "--include-metadata/--no-include-metadata",
        help="Include metadata files in matching",
    ),
    output_file: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file for match results (JSON format)",
        writable=True,
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output results in JSON format",
    ),
) -> None:
    """Match anime files against TMDB database.

    This command takes scanned anime files and matches them against the TMDB database
    to find corresponding TV shows and movies. It uses intelligent matching algorithms
    to handle various naming conventions and provides detailed matching results.

    Examples:
        anivault match .
        anivault match /path/to/anime --recursive --output match_results.json
        anivault match /path/to/anime --json
    """
    try:
        context = get_cli_context()

        match_options = MatchOptions(
            directory=DirectoryPath(path=directory),
            recursive=recursive,
            include_subtitles=include_subtitles,
            include_metadata=include_metadata,
            output=output_file,
            json_output=json_output,
            verbose=bool(context.verbose) if context else False,
        )

        exit_code = handle_match_command(match_options)

        if exit_code != 0:
            raise typer.Exit(exit_code)

    except ValueError as e:
        logger.exception("Validation error")
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e
