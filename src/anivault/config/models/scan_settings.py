"""Scan and filter configuration models.

This module contains configuration models for directory scanning
and file filtering operations.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from anivault.config.validators import validate_extensions_list, validate_patterns_list
from anivault.shared.constants import (
    Batch,
    ExclusionPatterns,
    FileSystem,
    Logging,
    SubtitleFormats,
    Timeout,
    VideoFormats,
    WorkerConfig,
)


class FilterSettings(BaseModel):
    """Configuration for the smart filtering engine.

    This class manages file filtering rules including extensions,
    patterns, and file/directory exclusions.
    """

    # File extension filtering
    allowed_extensions: list[str] = Field(
        default=list(VideoFormats.ALL_EXTENSIONS)
        + FileSystem.ADDITIONAL_VIDEO_FORMATS
        + SubtitleFormats.EXTENSIONS,
        description="List of allowed file extensions including video and subtitle files",
    )

    # File size filtering
    min_file_size_mb: int = Field(
        default=Logging.MIN_FILE_SIZE_MB,
        ge=0,
        description="Minimum file size in MB to include in scan",
    )

    # Filename pattern exclusion
    excluded_filename_patterns: list[str] = Field(
        default=ExclusionPatterns.FILENAME_PATTERNS,
        description="Filename patterns to exclude from scanning",
    )

    # Directory pattern exclusion
    excluded_dir_patterns: list[str] = Field(
        default=ExclusionPatterns.DIRECTORY_PATTERNS,
        description="Directory patterns to exclude from scanning",
    )

    # Hidden file/directory filtering
    skip_hidden_files: bool = Field(
        default=True,
        description="Skip files and directories starting with '.'",
    )

    # System file filtering
    skip_system_files: bool = Field(
        default=True,
        description="Skip system files and directories",
    )

    @field_validator("allowed_extensions")
    @classmethod
    def validate_extensions(cls, v: list[str]) -> list[str]:
        """Validate that extensions start with a dot."""
        return validate_extensions_list(v)

    @field_validator("excluded_filename_patterns", "excluded_dir_patterns")
    @classmethod
    def validate_patterns(cls, v: list[str]) -> list[str]:
        """Validate that patterns are non-empty strings."""
        return validate_patterns_list(v)


class ScanSettings(BaseModel):
    """Configuration for directory scanning.

    This class manages directory scanning behavior including
    batch processing, parallel execution, and worker settings.
    """

    # Note: File extensions are now managed by FilterSettings.allowed_extensions

    # Batch processing settings
    batch_size: int = Field(
        default=Batch.LARGE_SIZE,
        gt=0,
        description="Number of files to process in each batch",
    )

    # Worker settings
    max_workers: int = Field(
        default=WorkerConfig.DEFAULT,
        gt=0,
        description="Maximum number of worker threads",
    )

    # Timeout settings
    timeout: int = Field(
        default=Timeout.DEFAULT,
        gt=0,
        description="Timeout in seconds for file processing",
    )

    # Parallel scanning settings
    enable_parallel_scanning: bool = Field(
        default=True,
        description="Enable parallel directory scanning",
    )

    parallel_threshold: int = Field(
        default=Batch.PARALLEL_THRESHOLD,
        gt=0,
        description="Minimum file count to use parallel scanning",
    )

    # Filter configuration
    filter_config: FilterSettings = Field(
        default_factory=FilterSettings,
        description="Smart filtering configuration",
        alias="filter",
    )


# Backward compatibility aliases
FilterConfig = FilterSettings
ScanConfig = ScanSettings


__all__ = [
    "FilterConfig",  # Backward compatibility
    "FilterSettings",
    "ScanConfig",  # Backward compatibility
    "ScanSettings",
]
