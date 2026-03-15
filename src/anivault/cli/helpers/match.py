"""Match command helper functions.

Formatter/util only — output wrapper around match_formatters.
All orchestration (UseCase, services, pipeline) lives in match_handler.py.
"""

from __future__ import annotations

import sys

from rich.console import Console

from anivault.cli.json_formatter import format_json_output
from anivault.shared.constants.cli import CLIMessages
from anivault.shared.models.metadata import FileMetadata
from anivault.shared.types.cli import MatchOptions

from .match_formatters import collect_match_data, display_match_results

__all__ = [
    "collect_match_data",
    "display_match_results",
    "output_match_results",
]


def output_match_results(
    processed_results: list[FileMetadata],
    directory: str,
    options: MatchOptions,
    console: Console,
) -> None:
    """Emit match results as JSON to stdout or a rich TTY table.

    This is the single output entry point for the match command.
    Internally delegates to match_formatters for all formatting logic.

    Args:
        processed_results: List of matched FileMetadata instances
        directory: Scanned directory path string (for JSON summary)
        options: Match command options (controls json_output flag)
        console: Rich console for TTY output
    """
    if options.json_output:
        match_data = collect_match_data(processed_results, directory)
        json_output = format_json_output(
            success=True,
            command=CLIMessages.CommandNames.MATCH,
            data=match_data,
        )
        sys.stdout.buffer.write(json_output)
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
    else:
        display_match_results(processed_results, console)
