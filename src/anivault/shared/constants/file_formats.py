"""
File Format Constants

This module contains all constants related to file formats,
extensions, and file processing configuration.
"""

# Supported Video File Extensions
SUPPORTED_VIDEO_EXTENSIONS = (
    ".mkv",
    ".mp4",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".m4v",
    ".webm",
)

# Supported Video Extensions for Organize Command (includes .m4v)
SUPPORTED_VIDEO_EXTENSIONS_ORGANIZE = (
    ".mkv",
    ".mp4",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".m4v",
    ".webm",
)

# Supported Video Extensions for Match Command (excludes .m4v)
SUPPORTED_VIDEO_EXTENSIONS_MATCH = (
    ".mkv",
    ".mp4",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".webm",
)

# Metadata File Configuration
METADATA_FILENAME = "anivault_metadata.json"
METADATA_FILE_EXTENSION = ".json"

# Test File Extensions for Verification
TEST_FILE_EXTENSIONS = (".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".m4v", ".webm")

# Sample Test Filename
SAMPLE_TEST_FILENAME = "[SubsPlease] Jujutsu Kaisen S2 - 23 (1080p) [F02B9643].mkv"

# File Size Limits
MAX_FILE_SIZE = 1024 * 1024 * 1024  # 1GB in bytes
MIN_FILE_SIZE = 1024  # 1KB in bytes

# File Processing
MAX_FILENAME_LENGTH = 255  # maximum filename length
MAX_PATH_LENGTH = 4096  # maximum path length

# Additional Video Formats
ADDITIONAL_VIDEO_FORMATS = [".m2ts", ".ts"]

# Subtitle File Extensions
SUBTITLE_EXTENSIONS = [
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

# Excluded Filename Patterns
EXCLUDED_FILENAME_PATTERNS = [
    "*sample*",
    "*trailer*",
    "*preview*",
    "*teaser*",
    "*demo*",
    "*test*",
    "*temp*",
    "*tmp*",
]

# Excluded Directory Patterns
EXCLUDED_DIRECTORY_PATTERNS = [
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
