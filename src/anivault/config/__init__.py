"""AniVault Configuration Module

This module provides unified access to configuration models and settings
management for the AniVault application.

All configuration components are available through this package:
- Settings: Main configuration facade
- Loader functions: get_config, load_settings, reload_config, update_and_save_config
- Domain models: App, API, Scan, Cache, Performance, Folders, Security settings
- Backward-compatible aliases: *Config classes for gradual migration
"""

from __future__ import annotations

# Import Settings from models package
from .models.settings import Settings

# Import domain models from models package for backward compatibility
from .models import (
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

# Import loader functions directly from loader module to avoid circular dependency
from .loader import (
    get_config,
    load_settings,
    reload_config,
    update_and_save_config,
)

__all__ = [
    "APISettings",
    "AppConfig",
    "AppSettings",
    "CacheConfig",
    "CacheSettings",
    "FilterConfig",
    "FilterSettings",
    "FolderSettings",
    "LoggingConfig",
    "LoggingSettings",
    "PerformanceConfig",
    "PerformanceSettings",
    "ScanConfig",
    "ScanSettings",
    "SecuritySettings",
    "Settings",
    "TMDBConfig",
    "TMDBSettings",
    "get_config",
    "load_settings",
    "reload_config",
    "update_and_save_config",
]
