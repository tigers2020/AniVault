"""
Pydantic models for CLI argument validation.

This module provides Pydantic models for validating CLI arguments,
ensuring type safety and providing better error messages.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from anivault.shared.constants import FileSystem, RunDefaults


class DirectoryPath(BaseModel):
    """Validated directory path model."""

    path: Path = Field(..., description="Directory path")

    @field_validator("path")
    @classmethod
    def validate_directory(cls, v: Path) -> Path:
        """Validate that the path exists and is a directory."""
        if not v.exists():
            msg = f"Directory does not exist: {v}"
            raise ValueError(msg)
        if not v.is_dir():
            msg = f"Path is not a directory: {v}"
            raise ValueError(msg)
        if not os.access(v, os.R_OK):
            msg = f"Directory is not readable: {v}"
            raise ValueError(msg)
        return v


class FilePath(BaseModel):
    """Validated file path model."""

    path: Path = Field(..., description="File path")

    @field_validator("path")
    @classmethod
    def validate_file(cls, v: Path) -> Path:
        """Validate that the path exists and is a file."""
        if not v.exists():
            msg = f"File does not exist: {v}"
            raise ValueError(msg)
        if not v.is_file():
            msg = f"Path is not a file: {v}"
            raise ValueError(msg)
        if not os.access(v, os.R_OK):
            msg = f"File is not readable: {v}"
            raise ValueError(msg)
        return v


class ScanOptions(BaseModel):
    """Scan command options validation model."""

    directory: DirectoryPath = Field(..., description="Directory to scan")
    recursive: bool = Field(default=True, description="Scan recursively")
    include_subtitles: bool = Field(default=True, description="Include subtitle files")
    include_metadata: bool = Field(default=True, description="Include metadata files")
    output: Path | None = Field(default=None, description="Output file path")
    json_output: bool = Field(
        default=False,
        description="Output results in JSON format",
    )

    @field_validator("output")
    @classmethod
    def validate_output_path(cls, v: Path | None) -> Path | None:
        """Validate output path if provided."""
        if v is None:
            return v

        # Ensure parent directory exists
        v.parent.mkdir(parents=True, exist_ok=True)

        # Check if parent directory is writable
        if not os.access(v.parent, os.W_OK):
            msg = f"Output directory is not writable: {v.parent}"
            raise ValueError(msg)

        return v


class OrganizeOptions(BaseModel):
    """Organize command options validation model."""

    directory: DirectoryPath = Field(..., description="Directory to organize")
    dry_run: bool = Field(default=False, description="Preview changes without applying")
    yes: bool = Field(default=False, description="Skip confirmation prompts")
    enhanced: bool = Field(default=False, description="Use enhanced organization")
    destination: str = Field(default="Anime", description="Destination directory")
    extensions: str = Field(default="mkv,mp4,avi,mov,wmv,flv,webm,m4v", description="File extensions")
    json_output: bool = Field(default=False, description="JSON output format")
    verbose: bool = Field(default=False, description="Verbose output")


class MatchOptions(BaseModel):
    """Match command options validation model."""

    directory: DirectoryPath = Field(..., description="Directory to match")
    output: Path | None = Field(default=None, description="Output file path")
    force: bool = Field(
        default=False,
        description="Force re-matching of existing files",
    )
    recursive: bool = Field(default=True, description="Recursive matching")
    include_subtitles: bool = Field(default=True, description="Include subtitles")
    include_metadata: bool = Field(default=True, description="Include metadata")
    json_output: bool = Field(default=False, description="JSON output format")
    verbose: bool = Field(default=False, description="Verbose output")

    @field_validator("output")
    @classmethod
    def validate_output_path(cls, v: Path | None) -> Path | None:
        """Validate output path if provided."""
        if v is None:
            return v

        # Ensure parent directory exists
        v.parent.mkdir(parents=True, exist_ok=True)

        # Check if parent directory is writable
        if not os.access(v.parent, os.W_OK):
            msg = f"Output directory is not writable: {v.parent}"
            raise ValueError(msg)

        return v


class LogOptions(BaseModel):
    """Log command options validation model."""

    log_command: str = Field(
        ...,
        description="Log command to execute (list, show, tail)",
    )
    log_dir: DirectoryPath = Field(
        default_factory=lambda: DirectoryPath(path=Path(FileSystem.LOG_DIRECTORY)),
        description="Directory containing log files",
    )

    @field_validator("log_command")
    @classmethod
    def validate_log_command(cls, v: str) -> str:
        """Validate log command."""
        valid_commands = ["list", "show", "tail"]
        if v not in valid_commands:
            msg = f"Invalid log command '{v}'. Must be one of: {', '.join(valid_commands)}"
            raise ValueError(
                msg,
            )
        return v


class RollbackOptions(BaseModel):
    """Rollback command options validation model."""

    log_id: str = Field(..., description="ID of the operation log to rollback")
    dry_run: bool = Field(
        default=False,
        description="Preview rollback without applying",
    )
    yes: bool = Field(default=False, description="Skip confirmation prompts")

    @field_validator("log_id")
    @classmethod
    def validate_log_id(cls, v: str) -> str:
        """Validate log ID format."""
        if not v:
            raise ValueError("Log ID cannot be empty")

        # Basic validation for log ID format (timestamp-like)
        if len(v) < 10:
            raise ValueError("Log ID must be at least 10 characters long")

        return v


class VerifyOptions(BaseModel):
    """Verify command options validation model."""

    tmdb: bool = Field(default=False, description="Verify TMDB API connectivity")
    all: bool = Field(default=False, description="Verify all components")

    @field_validator("tmdb", "all", mode="before")
    @classmethod
    def validate_verify_options(cls, v: bool) -> bool:
        """Validate verify options."""
        return bool(v)


class RunOptions(BaseModel):
    """Run command options validation model."""

    directory: DirectoryPath = Field(description="Directory to process")
    recursive: bool = Field(default=True, description="Process files recursively")
    include_subtitles: bool = Field(default=True, description="Include subtitle files")
    include_metadata: bool = Field(default=True, description="Include metadata files")
    dry_run: bool = Field(default=False, description="Preview changes without applying")
    yes: bool = Field(default=False, description="Skip confirmation prompts")
    enhanced: bool = Field(default=False, description="Use enhanced organization")
    destination: str = Field(
        default=RunDefaults.DEFAULT_DESTINATION,
        description="Destination directory for organized files",
    )
    extensions: list[str] = Field(
        default_factory=lambda: RunDefaults.DEFAULT_EXTENSIONS,
        description="Video file extensions to process",
    )
    skip_scan: bool = Field(default=False, description="Skip scanning step")
    skip_match: bool = Field(default=False, description="Skip matching step")
    skip_organize: bool = Field(default=False, description="Skip organization step")
    max_workers: int = Field(default=RunDefaults.DEFAULT_MAX_WORKERS, description="Maximum number of worker threads")
    batch_size: int = Field(default=RunDefaults.DEFAULT_BATCH_SIZE, description="Batch size for processing")
    json_output: bool = Field(
        default=False,
        description="Output results in JSON format",
    )
    verbose: int = Field(default=0, description="Verbosity level")
