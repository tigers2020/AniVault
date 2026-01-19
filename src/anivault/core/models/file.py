"""
Data models for AniVault core operations.

This module defines the fundamental data structures used throughout
the AniVault system for file operations and organization.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from anivault.core.parser.models import ParsingResult


class OperationType(str, Enum):
    """Enumeration of supported file operations."""

    MOVE = "move"
    COPY = "copy"


@dataclass
class FileOperation:
    """
    Represents a single file operation to be performed.

    This model standardizes the representation of file operations
    throughout the AniVault system, replacing ad-hoc tuple structures.
    """

    operation_type: OperationType
    source_path: Path
    destination_path: Path

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return f"{self.operation_type.value}: {self.source_path} -> {self.destination_path}"


@dataclass
class ScannedFile:
    """
    Represents a scanned file with its metadata.

    This model combines file path information with parsed metadata,
    serving as the input for the FileOrganizer.
    """

    file_path: Path
    metadata: ParsingResult
    file_size: int = 0
    last_modified: float = 0.0

    @property
    def extension(self) -> str:
        """Get the file extension."""
        return self.file_path.suffix.lower()

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return f"ScannedFile: {self.file_path.name}"


__all__ = ["FileOperation", "OperationType", "ScannedFile"]
