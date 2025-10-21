"""Folder path and security configuration models.

This module contains configuration models for folder paths,
directory scanning, and security-related settings.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from anivault.config.validators import validate_folder_path as validate_folder_path_func
from anivault.config.validators import (
    validate_non_negative_int,
)


class FolderSettings(BaseModel):
    """Folder and directory settings (unified from TomlConfig + OrganizationConfig).

    This class manages folder paths, directory organization structure,
    and automatic scanning configuration.
    """

    source_folder: str = Field(
        default="",
        description="Source folder path for media files to organize",
    )
    target_folder: str = Field(
        default="",
        description="Target folder path for organized media files (required - must be configured)",
    )
    media_type: str = Field(
        default="anime",
        description="Media type for organization (anime, movie, etc.)",
    )
    structure: str = Field(
        default="season_##/korean_title/original_filename",
        description="Directory structure template for organization",
    )
    organize_by_resolution: bool = Field(
        default=False,
        description="Organize files by resolution (e.g., 1080p, 720p)",
    )
    organize_by_year: bool = Field(
        default=False,
        description="Organize files by release year (e.g., 2013, 2020)",
    )
    auto_scan_on_startup: bool = Field(
        default=False,
        description="Automatically scan source folder when application starts",
    )
    auto_scan_interval_minutes: int = Field(
        default=0,
        ge=0,
        le=1440,
        description="Auto scan interval in minutes (0 = disabled)",
    )
    include_subdirectories: bool = Field(
        default=True,
        description="Include subdirectories when scanning",
    )

    model_config = ConfigDict(
        validate_assignment=True,
    )

    @field_validator("source_folder", "target_folder")
    @classmethod
    def validate_folder_path(cls, v: str) -> str:
        """Validate folder path."""
        result = validate_folder_path_func(v)
        # Additional check: path should be absolute
        if v and v.strip():
            path = Path(v.strip())
            try:
                resolved_path = path.resolve()
                if not resolved_path.is_absolute():
                    raise ValueError("Folder path must be absolute")
            except (OSError, ValueError) as e:
                msg = f"Invalid folder path: {e}"
                raise ValueError(msg) from e
        return result

    @field_validator("auto_scan_interval_minutes")
    @classmethod
    def validate_scan_interval(cls, v: int) -> int:
        """Validate scan interval."""
        result = validate_non_negative_int(v)
        if v > 0 and v < 1:
            raise ValueError("Scan interval must be at least 1 minute")
        return result


class SecuritySettings(BaseModel):
    """Security-related settings (from TomlConfig).

    This class manages security configuration including encryption,
    key rotation, and PIN attempt limiting.

    NOTE: Security defaults will be reviewed in Task 13.
    """

    enable_encryption: bool = Field(
        default=True,
        description="Enable encryption for sensitive data",
    )
    key_rotation_days: int = Field(
        default=90,
        ge=1,
        le=365,
        description="Key rotation interval in days",
    )
    max_pin_attempts: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum PIN attempts before lockout",
    )
    lockout_duration_minutes: int = Field(
        default=30,
        ge=1,
        le=1440,
        description="Lockout duration in minutes",
    )


__all__ = [
    "FolderSettings",
    "SecuritySettings",
]
