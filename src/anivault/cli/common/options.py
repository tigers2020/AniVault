"""
Reusable Typer Options Module

This module provides reusable Typer options that can be imported and used
across all CLI commands. It ensures consistency and reduces code duplication
by centralizing common option definitions.

The options include:
- verbose: Verbosity level (count-based)
- log_level: Logging level (enum-based)
- json_output: JSON output mode (flag-based)
"""

from __future__ import annotations

from typing import Annotated

import typer

from anivault.cli.common.context import LogLevel

# Verbose option - count-based for multiple -v flags
verbose_option: Annotated[
    int,
    typer.Option(
        "--verbose",
        "-v",
        count=True,
        help="Enable verbose output (equivalent to --log-level DEBUG). Use multiple times for increased verbosity.",
    ),
] = 0


# Log level option - enum-based with case-insensitive choices
log_level_option: Annotated[
    LogLevel,
    typer.Option(
        "--log-level",
        case_sensitive=False,
        help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default: INFO.",
    ),
] = LogLevel.INFO


# JSON output option - flag-based
json_output_option: Annotated[
    bool,
    typer.Option(
        "--json",
        help="Enable machine-readable JSON output instead of human-readable format.",
    ),
] = False


# Version option - for main app only
version_option: Annotated[
    bool,
    typer.Option(
        "--version",
        "-V",
        help="Show version information and exit.",
        is_eager=True,
    ),
] = False
