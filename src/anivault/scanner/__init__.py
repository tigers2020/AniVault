"""Scanner module for AniVault.

This module provides file scanning functionality for discovering
media files in directory structures and parallel processing capabilities.
"""

from .extension_filter import (
    create_custom_extension_filter,
    create_media_extension_filter,
    get_default_media_filter,
    is_media_file,
    validate_extension_filter,
)
from .file_scanner import (
    get_media_files_count,
    scan_directory,
    scan_directory_paths,
    scan_directory_with_stats,
)
from .parser_worker import ParserWorker, ParserWorkerPool
from .producer_scanner import Scanner
from .scan_parse_pool import ScanParsePool

__all__ = [
    "scan_directory",
    "scan_directory_paths",
    "scan_directory_with_stats", 
    "get_media_files_count",
    "ParserWorker",
    "ParserWorkerPool",
    "Scanner",
    "ScanParsePool",
    "create_media_extension_filter",
    "create_custom_extension_filter",
    "get_default_media_filter",
    "is_media_file",
    "validate_extension_filter",
]
