"""AniVault Settings Configuration (DEPRECATED).

DEPRECATED: This module is kept for backward compatibility only.
Settings class has been moved to anivault.config.models.settings
to avoid circular dependencies and improve structure.

Please use:
    from anivault.config import Settings
    # or
    from anivault.config.models.settings import Settings
"""

from __future__ import annotations

import warnings

# Re-export Settings from models for backward compatibility
from anivault.config.models.settings import Settings

# Re-export domain models from models package for backward compatibility
from anivault.config.models import (
    APISettings,
    AppConfig,
    AppSettings,
    CacheConfig,
    CacheSettings,
    FilterConfig,
    FilterSettings,
    FolderSettings,
    LoggingConfig,
    LoggingSettings,
    PerformanceConfig,
    PerformanceSettings,
    ScanConfig,
    ScanSettings,
    SecuritySettings,
    TMDBConfig,
    TMDBSettings,
)

# Warn users about deprecated import path
warnings.warn(
    "Importing from anivault.config.settings is deprecated. "
    "Use 'from anivault.config import Settings' instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "APISettings",
    "AppConfig",  # Backward-compatible alias
    "AppSettings",
    "CacheConfig",  # Backward-compatible alias
    "CacheSettings",
    "FilterConfig",  # Backward-compatible alias
    "FilterSettings",
    "FolderSettings",
    "LoggingConfig",  # Backward-compatible alias
    "LoggingSettings",
    "PerformanceConfig",  # Backward-compatible alias
    "PerformanceSettings",
    "ScanConfig",  # Backward-compatible alias
    "ScanSettings",
    "SecuritySettings",
    "Settings",
    "TMDBConfig",  # Backward-compatible alias
    "TMDBSettings",
]
