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


def get_project_root() -> Path:
    """Get the project root directory path.

    Works in both development and PyInstaller bundled environments.
    Uses marker files (.git, pyproject.toml, setup.py) to identify project root.

    Returns:
        Absolute path to project root directory

    Raises:
        RuntimeError: If project root cannot be determined

    Example:
        >>> root = get_project_root()
        >>> cache_dir = root / "cache"
    """
    # Check if running as PyInstaller bundle
    if hasattr(sys, "_MEIPASS"):
        # In bundle, project root is typically the directory containing the executable
        # For GUI apps, use user home directory for cache/config
        # Return a writable location for cache files
        import os

        # Try to get executable directory
        if hasattr(sys, "executable") and sys.executable:
            exe_dir = Path(sys.executable).parent
            # Check if it looks like a project directory
            if (exe_dir / "config").exists() or (exe_dir / "cache").exists():
                logger.debug("Using executable directory as project root: %s", exe_dir)
                return exe_dir

        # Fallback: use current working directory
        cwd = Path.cwd()
        logger.debug("Using current working directory as project root: %s", cwd)
        return cwd

    # Development mode: find project root by looking for marker files
    current = Path(__file__).resolve()
    max_depth = 10  # Prevent infinite loops

    for _ in range(max_depth):
        # Check for common project root markers
        markers = [".git", "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt"]
        if any((current / marker).exists() for marker in markers):
            logger.debug("Found project root: %s", current)
            return current

        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent

    # Fallback: use directory containing src/ if it exists
    current = Path(__file__).resolve()
    for _ in range(max_depth):
        if (current / "src" / "anivault").exists():
            logger.debug("Found project root via src/ structure: %s", current)
            return current

        parent = current.parent
        if parent == current:
            break
        current = parent

    # Last resort: use current working directory
    cwd = Path.cwd()
    logger.warning(
        "Could not determine project root, using current directory: %s",
        cwd,
    )
    return cwd


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
