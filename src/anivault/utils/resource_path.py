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

_PROJECT_ROOT_MARKERS = (".git", "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt")
_MAX_ROOT_DEPTH = 10


def _resolve_bundle_root() -> Path | None:
    """Resolve project root when running as PyInstaller bundle. Returns None if not in bundle."""
    if not hasattr(sys, "_MEIPASS"):
        return None
    if hasattr(sys, "executable") and sys.executable:
        exe_dir = Path(sys.executable).parent
        if (exe_dir / "config").exists() or (exe_dir / "cache").exists():
            logger.debug("Using executable directory as project root: %s", exe_dir)
            return exe_dir
    cwd = Path.cwd()
    logger.debug("Using current working directory as project root: %s", cwd)
    return cwd


def _find_root_by_markers(start: Path) -> Path | None:
    """Walk up from start looking for project root markers. Returns None if not found."""
    current = start
    for _ in range(_MAX_ROOT_DEPTH):
        if any((current / m).exists() for m in _PROJECT_ROOT_MARKERS):
            logger.debug("Found project root: %s", current)
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _find_root_by_src_structure(start: Path) -> Path | None:
    """Walk up from start looking for src/anivault directory. Returns None if not found."""
    current = start
    for _ in range(_MAX_ROOT_DEPTH):
        if (current / "src" / "anivault").exists():
            logger.debug("Found project root via src/ structure: %s", current)
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


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
    bundle_root = _resolve_bundle_root()
    if bundle_root is not None:
        return bundle_root

    file_path = Path(__file__).resolve()
    root = _find_root_by_markers(file_path)
    if root is not None:
        return root

    root = _find_root_by_src_structure(file_path)
    if root is not None:
        return root

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
        base_path = Path(sys._MEIPASS)  # type: ignore[attr-defined]  # pylint: disable=protected-access
        logger.debug("Running as PyInstaller bundle, base path: %s", base_path)
    except AttributeError:
        # Development mode - use package directory
        # Go up from utils -> anivault -> src -> project root
        base_path = Path(__file__).parent.parent.parent.parent
        logger.debug("Running in development mode, base path: %s", base_path)

    resource_path = base_path / relative_path
    logger.debug("Resolved resource path: %s -> %s", relative_path, resource_path)
    return resource_path
