"""Settings provider abstraction for DI and centralized config access.

This module provides a protocol and default implementation for loading settings,
enabling dependency injection and future caching/centralization of config access.

Design:
- SettingsProvider protocol defines the contract
- DefaultSettingsProvider wraps load_settings for backward compatibility
- Container can inject SettingsProvider for testability
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from anivault.config.loader import load_settings
from anivault.config.models.settings import Settings


class SettingsProvider(Protocol):
    """Protocol for settings loading - enables DI and testability."""

    def get_settings(self, config_path: str | Path | None = None) -> Settings:
        """Load and return Settings instance.

        Args:
            config_path: Optional path to config file. Uses default when None.

        Returns:
            Settings instance
        """
        ...


class DefaultSettingsProvider:
    """Default implementation wrapping load_settings."""

    def get_settings(self, config_path: str | Path | None = None) -> Settings:
        """Load settings from config file."""
        return load_settings(config_path)


_default_provider: DefaultSettingsProvider | None = None


def get_settings_provider() -> SettingsProvider:
    """Get the default settings provider (singleton)."""
    global _default_provider
    if _default_provider is None:
        _default_provider = DefaultSettingsProvider()
    return _default_provider
