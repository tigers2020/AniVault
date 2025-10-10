"""
CLI-related Type Definitions

This module provides type aliases for CLI option validation and parsing.

These types ensure CLI arguments are validated at the boundary,
preventing invalid data from propagating into the core logic.
"""

from __future__ import annotations

from pydantic import DirectoryPath, FilePath, conint

# File system types
# Note: Using simple assignment instead of TypeAlias for Python 3.9 compatibility
ValidDirectoryPath = DirectoryPath
ValidFilePath = FilePath

# CLI option types
PositiveInt = conint(gt=0)
NonNegativeInt = conint(ge=0)
PortNumber = conint(ge=1, le=65535)

# NOTE: Specific CLI option models will be added in Task 3 (CLI Type Safety)
