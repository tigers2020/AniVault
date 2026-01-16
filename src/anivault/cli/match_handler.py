"""Match command handler for AniVault CLI.

Refactored to use decorator pattern for cleaner, more maintainable code.
Core logic moved to cli.helpers.match module.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import typer

from anivault.cli.common.context import get_cli_context
from anivault.cli.common.error_decorator import handle_cli_errors
from anivault.shared.types.cli import CLIDirectoryPath as DirectoryPath, MatchOptions
from anivault.cli.common.setup_decorator import setup_handler
from anivault.cli.helpers.match import run_match_pipeline
from anivault.shared.constants import CLI
from anivault.shared.constants.cli import CLIMessages

logger = logging.getLogger(__name__)


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
    console = kwargs.get("console")
    logger_adapter = kwargs.get("logger_adapter", logger)

    logger_adapter.info(CLI.INFO_COMMAND_STARTED.format(command=CLIMessages.CommandNames.MATCH))

    # Run async pipeline
    result = asyncio.run(run_match_pipeline(options, console))

    if result == 0:
        logger_adapter.info(CLI.INFO_COMMAND_COMPLETED.format(command=CLIMessages.CommandNames.MATCH))
    else:
        logger_adapter.error("Match command failed with exit code %s", result)

    return result


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
