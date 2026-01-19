"""Backward-compatible CLI option models.

This module preserves the legacy import path for CLI option models.
Prefer importing from anivault.shared.types.cli in new code.
"""

from __future__ import annotations

from anivault.shared.types.cli import (
    CLIDirectoryPath as DirectoryPath,
    CLIFilePath as FilePath,
    LogOptions,
    MatchOptions,
    OrganizeOptions,
    RunOptions,
    ScanOptions,
    VerifyOptions,
)

__all__ = [
    "DirectoryPath",
    "FilePath",
    "LogOptions",
    "MatchOptions",
    "OrganizeOptions",
    "RunOptions",
    "ScanOptions",
    "VerifyOptions",
]
