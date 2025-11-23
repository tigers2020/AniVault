"""Configuration domain models.

This module provides centralized access to all configuration models
that were refactored from the monolithic settings.py file.

All models are available with both their new names (*Settings) and
backward-compatible aliases (*Config) for gradual migration.
"""

from __future__ import annotations

# API Settings
from .api_settings import APISettings, TMDBConfig, TMDBSettings

# Application Settings
from .app_settings import AppConfig, AppSettings, LoggingConfig, LoggingSettings

# Cache Settings
from .cache_settings import CacheConfig, CacheSettings

# Folder and Security Settings
from .folder_security_settings import FolderSettings, SecuritySettings

# Grouping Settings
from .grouping_settings import GroupingSettings

# Performance Settings
from .performance_settings import PerformanceConfig, PerformanceSettings

# Scan and Filter Settings
from .scan_settings import FilterConfig, FilterSettings, ScanConfig, ScanSettings

# Main Settings class
from .settings import Settings

__all__ = [
    # All exports in alphabetical order
    "APISettings",
    "AppConfig",  # Backward compatibility alias
    "AppSettings",
    "CacheConfig",  # Backward compatibility alias
    "CacheSettings",
    "FilterConfig",  # Backward compatibility alias
    "FilterSettings",
    "FolderSettings",
    "GroupingSettings",
    "LoggingConfig",  # Backward compatibility alias
    "LoggingSettings",
    "PerformanceConfig",  # Backward compatibility alias
    "PerformanceSettings",
    "ScanConfig",  # Backward compatibility alias
    "ScanSettings",
    "SecuritySettings",
    "Settings",  # Main settings facade
    "TMDBConfig",  # Backward compatibility alias
    "TMDBSettings",
]
