"""
Theme Cache for AniVault GUI

This module provides QSS content caching with mtime-based validation,
reducing file I/O overhead for frequently accessed themes.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from anivault.core.data_structures.linked_hash_table import LinkedHashTable
from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext

from .theme_validator import ThemeValidator

logger = logging.getLogger(__name__)


class ThemeCache:
    """Manages QSS content caching with mtime-based validation.

    This class handles:
    - Mtime-based cache validation (cache hit if mtime matches)
    - Cache miss handling (load content and cache with new mtime)
    - Selective cache invalidation (specific theme or all themes)
    - Integrated theme name validation for cache refresh

    Cache Structure:
        LinkedHashTable[Path, tuple[mtime_ns: int, content: str]]

    Dependencies:
        - ThemeValidator: For theme name validation during refresh
        - LinkedHashTable: For O(1) cache operations
    """

    def __init__(self, validator: ThemeValidator) -> None:
        """Initialize theme cache.

        Args:
            validator: ThemeValidator instance for theme name validation
        """
        self._validator = validator
        # QSS content cache: LinkedHashTable[Path, (mtime_ns, content)]
        self._cache = LinkedHashTable[Path, tuple[int, str]](
            initial_capacity=16,
            load_factor=0.75,
        )

    def get_or_load(self, path: Path, loader: Callable[[Path], str]) -> str:
        """Get theme content from cache or load and cache it.

        Implements mtime-based cache validation:
        - Cache hit: If mtime matches, return cached content
        - Cache miss: Load content using loader, cache with new mtime

        Args:
            path: Path to the QSS file
            loader: Callable to load QSS content (e.g., _read_file_with_imports)

        Returns:
            QSS content as string

        Raises:
            ApplicationError: If file cannot be read or accessed
        """
        # Get current mtime
        try:
            mtime_ns = path.stat().st_mtime_ns
        except OSError as e:
            logger.exception("Failed to stat theme file: %s", path)
            raise ApplicationError(
                ErrorCode.FILE_NOT_FOUND,
                f"Theme file not accessible: {path}",
                ErrorContext(file_path=str(path)),
            ) from e

        # Check cache
        cached = self._cache.get(path)
        if cached and cached[0] == mtime_ns:
            logger.debug("Cache hit for theme: %s", path.name)
            return cached[1]

        # Cache miss - load and cache
        logger.debug("Cache miss for theme: %s (loading)", path.name)
        content = loader(path)
        self._cache.put(path, (mtime_ns, content))

        return content

    def refresh(self, theme_name: str | None = None) -> None:
        """Invalidate and refresh theme cache.

        This is a manual cache invalidation method for development/debugging.
        Normal theme operations automatically handle cache invalidation via
        mtime-based validation.

        Args:
            theme_name: Specific theme to refresh, or None for all themes

        Usage:
            # Development: Clear all cache after editing QSS files
            cache.refresh()

            # Clear specific theme cache
            cache.refresh("dark")

        Notes:
            - PUBLIC method for power users and development tools
            - NOT exposed in GUI menu (internal/dev feature)
            - Can be called from CLI debug mode or test fixtures
            - Automatic mtime validation usually makes this unnecessary
        """
        if theme_name is None:
            # Clear entire cache
            count = self._cache.size
            for path, _ in list(self._cache):
                self._cache.remove(path)
            logger.debug("Cleared entire theme cache (%d entries)", count)
        else:
            # Validate theme name
            theme_name = self._validator.validate_theme_name(theme_name)

            # Clear specific theme entries
            # Match by Path.stem (filename without extension)
            to_remove = [
                path
                for path, _ in self._cache
                if path.stem == theme_name or path.name == f"{theme_name}.qss"
            ]

            for path in to_remove:
                self._cache.remove(path)

            logger.debug(
                "Cleared cache for theme '%s' (%d entries)",
                theme_name,
                len(to_remove),
            )

    def clear(self) -> None:
        """Clear all cached theme content.

        This is a convenience method equivalent to refresh(None).
        """
        self.refresh(None)

    def __len__(self) -> int:
        """Return the number of cached themes."""
        return self._cache.size

    def __contains__(self, path: Path) -> bool:
        """Check if a theme path is cached."""
        return path in self._cache
