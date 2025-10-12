"""
QSS Loader for AniVault GUI

This module provides QSS file loading with @import directive resolution,
circular import detection, and performance monitoring.
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path

from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext

from .path_resolver import ThemePathResolver
from .theme_cache import ThemeCache
from .theme_validator import ThemeValidator

# Regular expression to detect @import directives in QSS files
# Matches: @import url("path/to/file.qss"); or @import url('path/to/file.qss');
# Captures the path in a named group
QSS_IMPORT_PATTERN = re.compile(
    r'^\s*@import\s+url\(["\']?(?P<path>[^"\']+)["\']?\)\s*;\s*$',
    re.MULTILINE,
)

# Maximum recursion depth for @import resolution (security limit)
MAX_IMPORT_DEPTH = 10


class QSSLoader:
    """Loads QSS files with @import resolution and caching.

    This class handles:
    - QSS file loading from resolved paths
    - @import directive resolution (recursive)
    - Circular import detection (security)
    - Maximum depth limit (DoS prevention)
    - Performance monitoring (50ms threshold)
    - Integration with ThemeCache for mtime-based caching

    Architecture:
        ThemeValidator ← ThemePathResolver ← ThemeCache ← QSSLoader
        - Validator: Path security validation
        - PathResolver: Theme file path resolution
        - Cache: Mtime-based content caching
        - QSSLoader: @import resolution and loading

    Dependencies:
        - ThemeValidator: For secure import path validation
        - ThemePathResolver: For theme file path resolution
        - ThemeCache: For mtime-based content caching
    """

    def __init__(
        self,
        validator: ThemeValidator,
        path_resolver: ThemePathResolver,
        cache: ThemeCache,
        max_depth: int = MAX_IMPORT_DEPTH,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize QSS loader.

        Args:
            validator: ThemeValidator for import path security
            path_resolver: ThemePathResolver for theme file paths
            cache: ThemeCache for mtime-based caching
            max_depth: Maximum @import recursion depth (default: 10)
            logger: Optional logger (default: module logger)
        """
        self._validator = validator
        self._path_resolver = path_resolver
        self._cache = cache
        self._max_depth = max_depth
        self._logger = logger or logging.getLogger(__name__)

    def load(self, theme_name: str) -> str:
        """Load QSS content from a theme file with @import resolution.

        Resolves @import directives recursively and includes circular
        import detection and path security validation.

        Performance monitoring: Logs DEBUG timing for all loads,
        WARNING if loading exceeds 50ms (potential performance issue).

        If theme file cannot be found after all fallback attempts,
        returns empty string to allow application to continue with
        minimal styling.

        Args:
            theme_name: Name of the theme to load

        Returns:
            QSS content as string with all imports resolved,
            or empty string if theme not found (safe fallback)

        Raises:
            ApplicationError: If theme file read fails (not file-not-found)
        """
        start_time = time.perf_counter()
        qss_path = None

        try:
            qss_path = self._path_resolver.get_qss_path(theme_name)

            # Handle None return (all fallbacks exhausted)
            if qss_path is None:
                self._logger.warning(
                    "No theme file found for %s after all fallbacks, using empty stylesheet",
                    theme_name,
                    extra=ErrorContext(
                        file_path=f"{theme_name}.qss",
                        additional_data={
                            "stage": "final-fallback",
                            "theme_name": theme_name,
                            "fallback_result": "empty-stylesheet",
                        },
                    ).model_dump(),
                )
                return ""  # Safe fallback: empty stylesheet

            # Use cached @import-aware reader (mtime-based)
            content = self._cache.get_or_load(qss_path, self._read_with_imports)

            # Performance monitoring
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # Log performance metrics
            if elapsed_ms > 50:
                self._logger.warning(
                    "Theme loading exceeded 50ms threshold: %s (%.2fms)",
                    theme_name,
                    elapsed_ms,
                )
            else:
                self._logger.debug(
                    "Loaded theme content for: %s (%.2fms, with imports)",
                    theme_name,
                    elapsed_ms,
                )

            return content

        except ApplicationError as e:
            # Only catch FILE_NOT_FOUND from get_qss_path (not from imports)
            # Import errors should be raised, not swallowed
            if e.code == ErrorCode.FILE_NOT_FOUND and qss_path is not None:
                # This is an import error, not a theme file error - re-raise
                raise
            if e.code == ErrorCode.FILE_NOT_FOUND:
                # Theme file itself not found - safe fallback
                self._logger.warning(
                    "Theme file not found: %s, using empty stylesheet",
                    theme_name,
                    extra=ErrorContext(
                        file_path=str(qss_path) if qss_path else f"{theme_name}.qss",
                        additional_data={
                            "stage": "load-error",
                            "theme_name": theme_name,
                            "error_code": e.code.value,
                        },
                    ).model_dump(),
                )
                return ""  # Safe fallback for theme file not found
            raise  # Re-raise other ApplicationErrors
        except Exception as e:
            self._logger.exception("Failed to load theme content for %s", theme_name)
            raise ApplicationError(
                ErrorCode.FILE_READ_ERROR,
                f"Failed to load theme content for {theme_name}: {e}",
                ErrorContext(
                    file_path=str(qss_path) if qss_path else f"{theme_name}.qss",
                ),
            ) from e

    def _read_with_imports(
        self, qss_path: Path, visited: set[Path] | None = None
    ) -> str:
        """Read QSS file and resolve @import directives recursively.

        Supports @import url("path/to/file.qss"); syntax.
        Includes circular import detection and path security validation.

        Args:
            qss_path: Path to QSS file to read
            visited: Set of already visited paths (for circular detection)

        Returns:
            QSS content with all imports resolved

        Raises:
            ApplicationError: If circular import detected, invalid path,
                            or max depth exceeded
        """
        # Initialize visited set
        if visited is None:
            visited = set()

        # Check depth limit (security: prevent DoS)
        if len(visited) >= self._max_depth:
            self._logger.error("Max import depth exceeded: %d", len(visited))
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                f"Max QSS import depth exceeded ({self._max_depth})",
                ErrorContext(
                    operation="_read_with_imports",
                    additional_data={"depth": len(visited)},
                ),
            )

        # Validate and resolve path
        resolved_path = self._validator.validate_import_path(qss_path)

        # Check for circular imports
        if resolved_path in visited:
            self._logger.error("Circular QSS import detected: %s", resolved_path)
            visited_str = ", ".join(str(p) for p in visited)
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                f"Circular QSS import detected: {resolved_path}",
                ErrorContext(
                    operation="_read_with_imports",
                    additional_data={
                        "circular_path": str(resolved_path),
                        "visited_paths": visited_str,
                    },
                ),
            )

        # Mark as visited
        visited.add(resolved_path)

        try:
            # Read file content
            content = resolved_path.read_text(encoding="utf-8")
            lines = []

            # Process each line
            for line in content.splitlines():
                # Check for @import directive
                match = QSS_IMPORT_PATTERN.match(line)
                if match:
                    # Extract import path
                    import_path = match.group("path")
                    # Resolve relative to current file's directory
                    nested_path = resolved_path.parent / import_path

                    self._logger.debug(
                        "Processing QSS import: %s -> %s", import_path, nested_path
                    )

                    # Recursively read imported file
                    imported_content = self._read_with_imports(nested_path, visited)
                    lines.append(imported_content)
                else:
                    # Regular line (not an import)
                    lines.append(line)

            return "\n".join(lines)

        except FileNotFoundError as e:
            self._logger.exception("QSS file not found: %s", resolved_path)
            raise ApplicationError(
                ErrorCode.FILE_NOT_FOUND,
                f"QSS file not found: {resolved_path}",
                ErrorContext(file_path=str(resolved_path)),
            ) from e
        except OSError as e:
            self._logger.exception("Failed to read QSS file: %s", resolved_path)
            raise ApplicationError(
                ErrorCode.FILE_READ_ERROR,
                f"Failed to read QSS file: {resolved_path}",
                ErrorContext(file_path=str(resolved_path)),
            ) from e
