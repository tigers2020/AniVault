"""
File Format Constants

This module contains all constants related to file formats,
extensions, and file processing configuration.
"""

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
    ADDITIONAL_EXTENSIONS = [".m4v", ".m2ts", ".ts"]

    # All supported extensions
    ALL_EXTENSIONS = CORE_EXTENSIONS + tuple(ADDITIONAL_EXTENSIONS)

    # Command-specific extensions
    ORGANIZE_EXTENSIONS = ALL_EXTENSIONS  # includes .m4v
    MATCH_EXTENSIONS = CORE_EXTENSIONS  # excludes .m4v


class SubtitleFormats:
    """Subtitle format configuration constants."""

    EXTENSIONS = [
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


class ExclusionPatterns:
    """File and directory exclusion patterns."""

    # Filename patterns to exclude
    FILENAME_PATTERNS = [
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
    DIRECTORY_PATTERNS = [
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


# Backward compatibility aliases
SUPPORTED_VIDEO_EXTENSIONS = VideoFormats.ALL_EXTENSIONS
SUPPORTED_VIDEO_EXTENSIONS_ORGANIZE = VideoFormats.ORGANIZE_EXTENSIONS
SUPPORTED_VIDEO_EXTENSIONS_MATCH = VideoFormats.MATCH_EXTENSIONS
ADDITIONAL_VIDEO_FORMATS = VideoFormats.ADDITIONAL_EXTENSIONS
SUBTITLE_EXTENSIONS = SubtitleFormats.EXTENSIONS
METADATA_FILENAME = MetadataConfig.FILENAME
METADATA_FILE_EXTENSION = MetadataConfig.EXTENSION
TEST_FILE_EXTENSIONS = TestConfig.EXTENSIONS
SAMPLE_TEST_FILENAME = TestConfig.SAMPLE_FILENAME
MAX_FILE_SIZE = FileLimits.MAX_SIZE
MIN_FILE_SIZE = FileLimits.MIN_SIZE
MAX_FILENAME_LENGTH = FileLimits.MAX_FILENAME_LENGTH
MAX_PATH_LENGTH = FileLimits.MAX_PATH_LENGTH
EXCLUDED_FILENAME_PATTERNS = ExclusionPatterns.FILENAME_PATTERNS
EXCLUDED_DIRECTORY_PATTERNS = ExclusionPatterns.DIRECTORY_PATTERNS
