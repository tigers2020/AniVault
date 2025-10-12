"""
AniVault Type Definitions Module

This module provides common Pydantic models and type aliases for AniVault,
ensuring type safety and eliminating dict/Any usage across the codebase.

The type hierarchy follows these principles:
- BaseTypeModel: Common base with lenient extra field handling
- StrictModel: Strict validation for critical data structures
- Type aliases: Domain-specific type definitions (API, CLI, Cache)
- Gradual migration: Coexists with legacy code via feature flags

Usage Example:
    >>> from anivault.shared.types import BaseTypeModel, TMDBId
    >>> class Media(BaseTypeModel):
    ...     id: TMDBId
    ...     name: str
    >>> media = Media(id=123, name="Attack on Titan")
"""

from __future__ import annotations

from .api import ISODate, LanguageCode, NonEmptyStr, TMDBId
from .base import BaseTypeModel, StrictModel
from .cache import CacheKey, Timestamp
from .cli import (
    CLIDirectoryPath,
    CLIFilePath,
    LogOptions,
    MatchOptions,
    NonNegativeInt,
    OrganizeOptions,
    PortNumber,
    PositiveInt,
    RollbackOptions,
    RunOptions,
    ScanOptions,
    VerifyOptions,
)
from .conversion import ModelConverter

__all__ = [
    "BaseTypeModel",
    "CLIDirectoryPath",
    "CLIFilePath",
    "CacheKey",
    "ISODate",
    "LanguageCode",
    "LogOptions",
    "MatchOptions",
    "ModelConverter",
    "NonEmptyStr",
    "NonNegativeInt",
    "OrganizeOptions",
    "PortNumber",
    "PositiveInt",
    "RollbackOptions",
    "RunOptions",
    "ScanOptions",
    "StrictModel",
    "TMDBId",
    "Timestamp",
    "VerifyOptions",
]

__version__ = "0.1.0"
