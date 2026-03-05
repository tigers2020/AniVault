"""Shared formatting utilities for CLI helpers.

Extracted to eliminate duplication across match, organize, and scan modules.
"""

from __future__ import annotations

from pathlib import Path


def format_size(size_bytes: float) -> str:
    """Format size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string (e.g., "1.5 GB")
    """
    bytes_per_unit = 1024.0

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < bytes_per_unit:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= bytes_per_unit
    return f"{size_bytes:.1f} PB"


def get_file_size(file_path: str | Path) -> int:
    """Get file size in bytes, returning 0 on error.

    Args:
        file_path: Path to file

    Returns:
        File size in bytes, or 0 if error
    """
    try:
        return Path(file_path).stat().st_size
    except (OSError, TypeError):
        return 0
