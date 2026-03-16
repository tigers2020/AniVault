"""
File format constants for parsing (S5: extracted from shared.constants.file_formats).
"""

from __future__ import annotations

from typing import ClassVar

# File size limits (1KB, 1GB - aligned with FileSystem)
_MIN_FILE_SIZE = 1024
_MAX_FILE_SIZE = 1024**3


class VideoFormats:
    """Video format configuration constants."""

    CORE_EXTENSIONS = (
        ".mkv",
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
    )

    ADDITIONAL_EXTENSIONS: ClassVar[list[str]] = [".m4v", ".m2ts", ".ts"]

    ALL_EXTENSIONS = CORE_EXTENSIONS + tuple(ADDITIONAL_EXTENSIONS)

    ORGANIZE_EXTENSIONS = ALL_EXTENSIONS
    MATCH_EXTENSIONS = CORE_EXTENSIONS


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

    MAX_SIZE = _MAX_FILE_SIZE
    MIN_SIZE = _MIN_FILE_SIZE
    MAX_FILENAME_LENGTH = 255
    MAX_PATH_LENGTH = 4096


class VideoQuality:
    """Video quality and resolution classification constants."""

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

    LOW_RESOLUTION: ClassVar[list[str]] = [
        "720p",
        "576p",
        "480p",
        "SD",
        "360p",
        "240p",
        "144p",
    ]

    LOW_RES_FOLDER = "low_res"

    @classmethod
    def is_high_resolution(cls, quality: str | None) -> bool:
        """Check if quality string indicates high resolution."""
        if not quality:
            return False
        quality_upper = quality.upper()
        for high_res in cls.HIGH_RESOLUTION:
            if high_res.upper() in quality_upper:
                return True
        for low_res in cls.LOW_RESOLUTION:
            if low_res.upper() in quality_upper:
                return False
        return False


class ExclusionPatterns:
    """File and directory exclusion patterns."""

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


__all__ = [
    "ExclusionPatterns",
    "FileLimits",
    "MetadataConfig",
    "SubtitleFormats",
    "VideoFormats",
    "VideoQuality",
]
