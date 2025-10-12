"""
Pydantic models for CLI argument validation.

This module re-exports CLI option models from anivault.shared.types
for backward compatibility during migration.

DEPRECATED: Import directly from anivault.shared.types.cli instead.
This module will be removed after all imports are updated.
"""

from __future__ import annotations

# Re-export from shared.types for backward compatibility
from anivault.shared.types.cli import CLIDirectoryPath as DirectoryPath
from anivault.shared.types.cli import CLIFilePath as FilePath
from anivault.shared.types.cli import (
    LogOptions,
    MatchOptions,
    OrganizeOptions,
    RollbackOptions,
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
    "RollbackOptions",
    "RunOptions",
    "ScanOptions",
    "VerifyOptions",
]
