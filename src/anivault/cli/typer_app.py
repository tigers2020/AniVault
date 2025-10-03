"""
AniVault Typer CLI Application

This is the main Typer-based CLI application for AniVault.
It provides a modern, type-safe command-line interface with automatic
help generation, shell completion, and better error handling.
"""

from __future__ import annotations

import typer

# Create the main Typer app
app = typer.Typer(
    name="anivault",
    help="AniVault - Advanced Anime Collection Management System",
    add_completion=False,  # Will be enabled later
    rich_markup_mode="rich",  # Enable rich formatting
    no_args_is_help=True,
)

# Version information
__version__ = "0.1.0"


def version_callback(value: bool) -> None:
    """Print version information and exit."""
    if value:
        typer.echo(f"AniVault CLI v{__version__}")
        raise typer.Exit


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version information and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """
    AniVault - Advanced Anime Collection Management System

    A comprehensive tool for organizing anime collections with TMDB integration,
    intelligent file matching, and automated organization capabilities.

    AniVault helps you scan, identify, and organize your anime files into
    structured directories with proper metadata enrichment.
    """


if __name__ == "__main__":
    app()
