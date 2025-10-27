"""
File Format Constants

This module contains all constants related to file formats,
extensions, and file processing configuration.
"""

from __future__ import annotations

from typing import ClassVar

from .system import FileSystem


class VideoFormats:
    """Video format configuration constants."""

    # Core video extensions
    CORE_EXTENSIONS = (
        ".mkv",
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
    )

    # Additional extensions
    ADDITIONAL_EXTENSIONS: ClassVar[list[str]] = [".m4v", ".m2ts", ".ts"]

    # All supported extensions
    ALL_EXTENSIONS = CORE_EXTENSIONS + tuple(ADDITIONAL_EXTENSIONS)

    # Command-specific extensions
    ORGANIZE_EXTENSIONS = ALL_EXTENSIONS  # includes .m4v
    MATCH_EXTENSIONS = CORE_EXTENSIONS  # excludes .m4v


class SubtitleFormats:
    """Subtitle format configuration constants."""

    EXTENSIONS: ClassVar[list[str]] = [
        ".srt",
        ".ass",
        ".ssa",
        ".sub",
        ".idx",
        ".vtt",
        ".smi",
        ".sami",
        ".mks",
        ".sup",
        ".pgs",
        ".dvb",
    ]


class MetadataConfig:
    """Metadata file configuration constants."""

    FILENAME = "anivault_metadata.json"
    EXTENSION = ".json"


class FileLimits:
    """File size and path limits."""

    # File sizes (inherited from system constants)
    MAX_SIZE = FileSystem.MAX_FILE_SIZE  # 1GB
    MIN_SIZE = FileSystem.MIN_FILE_SIZE  # 1KB

    # Path limits (inherited from system constants)
    MAX_FILENAME_LENGTH = FileSystem.MAX_FILENAME_LENGTH  # 255
    MAX_PATH_LENGTH = FileSystem.MAX_PATH_LENGTH  # 4096


class TestConfig:
    """Test file configuration constants."""

    # Test file extensions
    EXTENSIONS = VideoFormats.ALL_EXTENSIONS

    # Sample test filename
    SAMPLE_FILENAME = "[SubsPlease] Jujutsu Kaisen S2 - 23 (1080p) [F02B9643].mkv"


class VideoQuality:
    """Video quality and resolution classification constants."""

    # High resolution formats (keep in regular folder structure)
    HIGH_RESOLUTION: ClassVar[list[str]] = [
        "1080p",
        "1080i",
        "2160p",
        "4K",
        "UHD",
        "8K",
        "2K",
        "QHD",
    ]

    # Low resolution formats (move to low_res folder)
    LOW_RESOLUTION: ClassVar[list[str]] = [
        "720p",
        "576p",
        "480p",
        "SD",
        "360p",
        "240p",
        "144p",
    ]

    # Folder name for low resolution files
    LOW_RES_FOLDER = "low_res"

    @classmethod
    def is_high_resolution(cls, quality: str | None) -> bool:
        """Check if quality string indicates high resolution.

        Args:
            quality: Quality string from parsed metadata (e.g., "1080p", "720p")

        Returns:
            True if high resolution, False otherwise
        """
        if not quality:
            return False  # Default to low resolution if unknown

        quality_upper = quality.upper()

        # Check high resolution patterns
        for high_res in cls.HIGH_RESOLUTION:
            if high_res.upper() in quality_upper:
                return True

        # Check low resolution patterns
        for low_res in cls.LOW_RESOLUTION:
            if low_res.upper() in quality_upper:
                return False

        # Default to low resolution if pattern not recognized
        return False


class ExclusionPatterns:
    """File and directory exclusion patterns."""

    # Filename patterns to exclude
    FILENAME_PATTERNS: ClassVar[list[str]] = [
        "*sample*",
        "*trailer*",
        "*preview*",
        "*teaser*",
        "*demo*",
        "*test*",
        "*temp*",
        "*tmp*",
    ]

    # Directory patterns to exclude
    DIRECTORY_PATTERNS: ClassVar[list[str]] = [
        ".git",
        ".svn",
        ".hg",
        "$RECYCLE.BIN",
        "System Volume Information",
        "Thumbs.db",
        "__pycache__",
        ".pytest_cache",
        "node_modules",
        ".vscode",
        ".idea",
        ".DS_Store",
        "lost+found",
    ]
