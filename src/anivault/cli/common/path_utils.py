"""Path utility functions for CLI commands.

This module provides common path manipulation and extraction utilities
used across CLI handlers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def extract_directory_path(directory_option: Any) -> Path:
    """Extract Path from directory option.

    Handles both CLIDirectoryPath objects and direct Path/str values.

    Args:
        directory_option: Directory option value (CLIDirectoryPath, Path, or str)

    Returns:
        Extracted Path object

    Examples:
        >>> from anivault.shared.types.cli import CLIDirectoryPath
        >>> # With CLIDirectoryPath
        >>> cli_path = CLIDirectoryPath(path=Path("/some/dir"))
        >>> extract_directory_path(cli_path)
        PosixPath('/some/dir')
        >>> # With direct Path
        >>> extract_directory_path(Path("/some/dir"))
        PosixPath('/some/dir')
        >>> # With str
        >>> extract_directory_path("/some/dir")
        PosixPath('/some/dir')
    """
    if hasattr(directory_option, "path"):
        # CLIDirectoryPath has a .path attribute that is already a Path
        return Path(directory_option.path)
    # Convert str or Path-like object to Path
    return Path(directory_option)
