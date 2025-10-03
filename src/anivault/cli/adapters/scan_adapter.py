"""
Scan Command Adapter

This module provides the adapter for the scan command, converting Typer
parameters to the format expected by the legacy argparse handler.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import typer

from anivault.cli.adapters.base import BaseAdapter
from anivault.cli.scan_handler import handle_scan_command


class ScanAdapter(BaseAdapter):
    """
    Adapter for the scan command.

    Converts Typer parameters to argparse.Namespace format expected by
    the legacy handle_scan_command function.
    """

    def _convert_parameters(
        self,
        directory: Path,
        recursive: bool = True,
        include_subtitles: bool = True,
        include_metadata: bool = True,
        output_file: Path | None = None,
    ) -> argparse.Namespace:
        """
        Convert Typer parameters to argparse.Namespace for scan command.

        Args:
            directory: Directory to scan
            recursive: Whether to scan recursively
            include_subtitles: Whether to include subtitle files
            include_metadata: Whether to include metadata files
            output_file: Optional output file path

        Returns:
            argparse.Namespace compatible with handle_scan_command
        """
        # Create base namespace with common options
        namespace = self._create_base_namespace()

        # Add scan-specific options
        namespace.directory = str(directory)
        namespace.recursive = recursive
        namespace.include_subtitles = include_subtitles
        namespace.include_metadata = include_metadata
        namespace.output_file = str(output_file) if output_file else None

        return namespace

    def _get_command_name(self) -> str:
        """Get the command name for logging."""
        return "scan"


def create_scan_command() -> typer.Typer:
    """
    Create the scan command for Typer CLI.

    Returns:
        Configured Typer command for scan functionality
    """
    # Create the adapter
    adapter = ScanAdapter(handle_scan_command)

    # Create the Typer command
    command = typer.Typer(
        name="scan",
        help="Scan directories for anime files and extract metadata",
        rich_markup_mode="rich",
    )

    @command.command()
    def scan(
        directory: Path = typer.Argument(
            ...,
            help="Directory to scan for anime files",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
        ),
        recursive: bool = typer.Option(
            True,
            "--recursive",
            "-r",
            help="Scan directories recursively",
        ),
        include_subtitles: bool = typer.Option(
            True,
            "--include-subtitles",
            help="Include subtitle files in scan",
        ),
        include_metadata: bool = typer.Option(
            True,
            "--include-metadata",
            help="Include metadata files in scan",
        ),
        output_file: Path | None = typer.Option(
            None,
            "--output",
            "-o",
            help="Output file for scan results (JSON format)",
            writable=True,
        ),
    ) -> None:
        """
        Scan directories for anime files and extract metadata.

        This command recursively scans the specified directory for anime files
        and extracts metadata using anitopy. It can optionally include subtitle
        and metadata files in the scan results.

        Examples:
            # Scan current directory
            anivault-ng scan .

            # Scan with custom options
            anivault-ng scan /path/to/anime --recursive --output results.json

            # Scan without subtitles
            anivault-ng scan /path/to/anime --no-include-subtitles
        """
        # Call the adapter
        exit_code = adapter(
            directory=directory,
            recursive=recursive,
            include_subtitles=include_subtitles,
            include_metadata=include_metadata,
            output_file=output_file,
        )

        # Exit with the appropriate code
        if exit_code != 0:
            raise typer.Exit(exit_code)

    return command
