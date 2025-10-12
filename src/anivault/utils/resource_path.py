"""
Resource Path Utilities for PyInstaller Compatibility

This module provides utilities for accessing resources in both development
and PyInstaller bundled environments.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def get_resource_path(relative_path: str) -> Path:
    """Get absolute path to resource, works for dev and PyInstaller bundle.

    In development mode, resources are accessed from the source directory.
    In PyInstaller bundles, resources are extracted to a temporary directory
    accessible via sys._MEIPASS.

    Args:
        relative_path: Relative path from package root (e.g., "anivault/resources/themes")

    Returns:
        Absolute path to the resource

    Example:
        >>> themes_dir = get_resource_path("anivault/resources/themes")
        >>> config_file = get_resource_path("config/config.toml")
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        logger.debug("Running as PyInstaller bundle, base path: %s", base_path)
    except AttributeError:
        # Development mode - use package directory
        # Go up from utils -> anivault -> src -> project root
        base_path = Path(__file__).parent.parent.parent.parent
        logger.debug("Running in development mode, base path: %s", base_path)

    resource_path = base_path / relative_path
    logger.debug("Resolved resource path: %s -> %s", relative_path, resource_path)
    return resource_path
