"""File system related constants."""

from __future__ import annotations

from typing import ClassVar

from .base import BASE_FILE_SIZE


class FileSystem:
    """File system related constants."""

    # Base file sizes
    MIN_FILE_SIZE = BASE_FILE_SIZE  # 1KB
    MAX_FILE_SIZE = BASE_FILE_SIZE**3  # 1GB

    # Path limits
    MAX_PATH_LENGTH = 4096
    MAX_FILENAME_LENGTH = 255

    # Directory names
    LOG_DIRECTORY = "logs"
    CONFIG_DIRECTORY = "config"
    CACHE_BACKEND = "memory"
    HOME_DIR = ".anivault"
    CACHE_DIRECTORY = "cache"
    OUTPUT_DIRECTORY = "output"
    RESULTS_DIRECTORY = "results"

    # Exclusion patterns
    EXCLUDED_DIRECTORY_PATTERNS: ClassVar[list[str]] = [
        "__pycache__",
        ".git",
        ".svn",
        ".hg",
        "node_modules",
        ".vscode",
        ".idea",
        "venv",
        "env",
        ".env",
    ]
    EXCLUDED_FILENAME_PATTERNS: ClassVar[list[str]] = [
        "*.tmp",
        "*.temp",
        "*.log",
        "*.cache",
        "*.bak",
        "*.swp",
        "*.swo",
        "*.orig",
        "*.rej",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        "*.so",
        "*.dll",
        "*.exe",
    ]

    # Media file extensions
    # NOTE: For new code, prefer VideoFormats.ALL_EXTENSIONS from file_formats module
    # These are kept for backward compatibility
    VIDEO_EXTENSIONS: ClassVar[list[str]] = [
        ".mkv",
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".m4v",
        ".webm",
        ".m2ts",
        ".ts",
    ]

    # CLI default video extensions (subset for CLI commands)
    # NOTE: For new code, prefer VideoFormats.CORE_EXTENSIONS from file_formats module
    CLI_VIDEO_EXTENSIONS: ClassVar[list[str]] = [
        ".mkv",
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
        ".m4v",
    ]
    # NOTE: For new code, prefer SubtitleFormats.EXTENSIONS from file_formats module
    SUBTITLE_EXTENSIONS: ClassVar[list[str]] = [
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
    SUPPORTED_VIDEO_EXTENSIONS: ClassVar[list[str]] = VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS
    SUPPORTED_VIDEO_EXTENSIONS_MATCH: ClassVar[list[str]] = VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS
    SUPPORTED_VIDEO_EXTENSIONS_ORGANIZE: ClassVar[list[str]] = VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS

    # File patterns
    LOG_FILE_PATTERN = "*.log"
    CACHE_FILE_PATTERN = "*.cache"
    CONFIG_FILE_PATTERN = "*.toml"
    JSON_FILE_PATTERN = "*.json"
    ADDITIONAL_VIDEO_FORMATS: ClassVar[list[str]] = [
        ".m2ts",
        ".ts",
        ".mts",
        ".m2v",
        ".m1v",
        ".mpg",
        ".mpeg",
        ".mpe",
        ".mpv",
        ".mp2",
        ".mp3",
        ".mpa",
        ".mpe",
        ".mpg",
        ".mpeg",
        ".m1v",
        ".m2v",
        ".mpv",
        ".mp2",
        ".mp3",
        ".mpa",
    ]


class Encoding:
    """Text encoding constants."""

    DEFAULT = "utf-8"
    FALLBACK = "cp1252"
    UTF8_BOM = "utf-8-sig"


__all__ = ["Encoding", "FileSystem"]
