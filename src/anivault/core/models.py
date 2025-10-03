"""
Data models for AniVault core operations.

This module defines the fundamental data structures used throughout
the AniVault system for file operations and organization.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from anivault.core.parser.models import ParsingResult


class OperationType(str, Enum):
    """Enumeration of supported file operations."""

    MOVE = "move"
    COPY = "copy"


class FileOperation(BaseModel):
    """
    Represents a single file operation to be performed.

    This model standardizes the representation of file operations
    throughout the AniVault system, replacing ad-hoc tuple structures.
    """

    operation_type: OperationType = Field(
        ...,
        description="Type of operation to perform (move or copy)",
    )
    source_path: Path = Field(
        ...,
        description="Source path of the file or directory",
    )
    destination_path: Path = Field(
        ...,
        description="Destination path for the file or directory",
    )

    def model_post_init(self, __context: Any) -> None:
        """Validate paths after model initialization."""
        # Path fields are already validated by Pydantic

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return f"{self.operation_type.value}: {self.source_path} -> {self.destination_path}"


class ScannedFile(BaseModel):
    """
    Represents a scanned file with its metadata.

    This model combines file path information with parsed metadata,
    serving as the input for the FileOrganizer.
    """

    model_config = ConfigDict(
        # Optimize JSON serialization for file processing performance
        json_encoders={
            # Custom encoders for specific types if needed
        },
        # Use orjson for better performance in file processing
        json_schema_extra={
            "example": {
                "file_path": "/path/to/anime.mkv",
                "metadata": {"anime_title": "Attack on Titan", "episode_number": 1},
                "file_size": 1024000,
                "last_modified": 1640995200.0,
            },
        },
    )

    file_path: Path = Field(
        ...,
        description="Original path of the scanned file",
    )
    metadata: ParsingResult = Field(
        ...,
        description="Parsed metadata from the file",
    )
    file_size: int = Field(
        default=0,
        description="File size in bytes",
    )
    last_modified: float = Field(
        default=0.0,
        description="Last modification time as Unix timestamp",
    )

    def model_post_init(self, __context: Any) -> None:
        """Validate paths after model initialization."""
        # Path fields are already validated by Pydantic

    @property
    def extension(self) -> str:
        """Get the file extension."""
        return self.file_path.suffix.lower()

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return f"ScannedFile: {self.file_path.name}"
