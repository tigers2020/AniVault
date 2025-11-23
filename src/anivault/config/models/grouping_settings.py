"""File grouping configuration models.

This module contains configuration models for file grouping operations,
including matcher settings and performance limits.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class GroupingSettings(BaseModel):
    """Configuration for file grouping operations.

    This class manages settings for the grouping pipeline, including
    which matchers to use, size limits for performance, and similarity thresholds.

    Attributes:
        use_title_matcher: Whether to run Title matcher after Hash matcher.
                          Default: True
        max_title_match_group_size: Maximum number of files in a group for
                                   Title matcher processing. Groups larger than
                                   this will skip Title matcher (DoS protection).
                                   Default: 1000
        max_input_files: Maximum number of input files to process in a single
                        grouping operation. Exceeding this will raise an error.
                        Default: 10000 (DoS protection)
        title_similarity_threshold: Minimum similarity score (0.0-1.0) for
                                   Title matcher grouping. Default: 0.85

    Example:
        >>> settings = GroupingSettings(
        ...     use_title_matcher=True,
        ...     max_title_match_group_size=500,
        ...     title_similarity_threshold=0.9
        ... )
        >>> settings.use_title_matcher
        True
    """

    use_title_matcher: bool = Field(
        default=True,
        description="Whether to run Title matcher after Hash matcher in pipeline",
    )

    max_title_match_group_size: int = Field(
        default=150,
        ge=1,
        le=100000,
        description=(
            "Maximum number of files in a group for Title matcher processing. "
            "Groups larger than this will skip Title matcher (DoS protection)"
        ),
    )

    max_input_files: int = Field(
        default=10000,
        ge=1,
        le=1000000,
        description=(
            "Maximum number of input files to process in a single grouping operation. "
            "Exceeding this will raise an error (DoS protection)"
        ),
    )

    title_similarity_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score (0.0-1.0) for Title matcher grouping",
    )

    subtitle_matching_strategy: Literal["indexed", "fallback", "legacy"] = Field(
        default="indexed",
        description=(
            "Subtitle matching strategy: "
            "'indexed' uses index for O(f+s) performance (default), "
            "'fallback' uses index but falls back to full scan if lookup fails, "
            "'legacy' uses full directory scan for backward compatibility"
        ),
    )

    @field_validator("max_title_match_group_size")
    @classmethod
    def validate_max_title_match_group_size(cls, v: int) -> int:
        """Validate max_title_match_group_size is reasonable."""
        if v < 1:
            msg = "max_title_match_group_size must be at least 1"
            raise ValueError(msg)
        if v > 100000:
            msg = "max_title_match_group_size cannot exceed 100000 (DoS protection)"
            raise ValueError(msg)
        return v

    @field_validator("max_input_files")
    @classmethod
    def validate_max_input_files(cls, v: int) -> int:
        """Validate max_input_files is reasonable."""
        if v < 1:
            msg = "max_input_files must be at least 1"
            raise ValueError(msg)
        if v > 1000000:
            msg = "max_input_files cannot exceed 1000000 (DoS protection)"
            raise ValueError(msg)
        return v

    @field_validator("title_similarity_threshold")
    @classmethod
    def validate_title_similarity_threshold(cls, v: float) -> float:
        """Validate title_similarity_threshold is in valid range."""
        if not 0.0 <= v <= 1.0:
            msg = "title_similarity_threshold must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


__all__ = ["GroupingSettings"]
