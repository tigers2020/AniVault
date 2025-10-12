"""
Theme Manager for AniVault GUI

This module provides centralized theme management using PySide6 QSS files
to ensure consistent styling across the application.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from PySide6.QtWidgets import QApplication

from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext

logger = logging.getLogger(__name__)

# Regular expression to detect @import directives in QSS files
# Matches: @import url("path/to/file.qss"); or @import url('path/to/file.qss');
# Captures the path in a named group
QSS_IMPORT_PATTERN = re.compile(
    r'^\s*@import\s+url\(["\']?(?P<path>[^"\']+)["\']?\)\s*;\s*$',
    re.MULTILINE,
)

# Maximum recursion depth for @import resolution (security limit)
MAX_IMPORT_DEPTH = 10


class ThemeManager:
    """Manages application themes using QSS files."""

    # Available themes
    LIGHT_THEME = "light"
    DARK_THEME = "dark"
    DEFAULT_THEME = LIGHT_THEME

    def __init__(self, themes_dir: Path | None = None) -> None:
        """Initialize the ThemeManager.

        Args:
            themes_dir: Optional path to themes directory. If None, uses
                      default path in resources/themes/
        """
        if themes_dir is None:
            # Get the package directory and construct themes path
            package_dir = Path(__file__).parent.parent.parent
            self.themes_dir = package_dir / "resources" / "themes"
        else:
            self.themes_dir = Path(themes_dir)

        self.current_theme: str | None = None
        # QSS content cache: {Path: (mtime_ns, content)}
        self._qss_cache: dict[Path, tuple[int, str]] = {}
        self._ensure_themes_directory()

    def _ensure_themes_directory(self) -> None:
        """Ensure the themes directory exists."""
        try:
            self.themes_dir.mkdir(parents=True, exist_ok=True)
            logger.debug("Themes directory ensured: %s", self.themes_dir)
        except Exception as e:
            logger.exception("Failed to create themes directory")
            raise ApplicationError(
                ErrorCode.DIRECTORY_CREATION_FAILED,
                f"Failed to create themes directory: {e}",
                ErrorContext(file_path=str(self.themes_dir)),
            ) from e

    def get_available_themes(self) -> list[str]:
        """Get list of available theme names.

        Returns:
            List of available theme names
        """
        themes = []
        try:
            for qss_file in self.themes_dir.glob("*.qss"):
                theme_name = qss_file.stem
                themes.append(theme_name)
            logger.debug("Available themes: %s", themes)
            return themes
        except Exception:
            logger.exception("Failed to get available themes")
            return []

    def _validate_theme_name(self, theme_name: str) -> str:
        """Validate and sanitize theme name input.

        Args:
            theme_name: Raw theme name from user input

        Returns:
            str: Validated theme name (unchanged if valid)

        Raises:
            ApplicationError with ErrorCode.VALIDATION_ERROR if:
                - theme_name is empty or None
                - length > 50 characters
                - contains invalid characters (only alphanumeric, hyphen, underscore allowed)
                - contains path separators (/, \\, ..)
        """
        if not theme_name:
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                "Theme name cannot be empty",
                ErrorContext(operation="_validate_theme_name"),
            )

        if len(theme_name) > 50:
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                f"Theme name too long (max 50 characters): {len(theme_name)}",
                ErrorContext(
                    operation="_validate_theme_name",
                    additional_data={"theme_name": theme_name[:50]},
                ),
            )

        # Security: Prevent path traversal attacks
        if any(char in theme_name for char in ["/", "\\", ".."]):
            logger.error("Invalid theme name (path traversal attempt): %s", theme_name)
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                f"Invalid theme name (contains path separators): {theme_name}",
                ErrorContext(
                    operation="_validate_theme_name",
                    additional_data={"theme_name": theme_name},
                ),
            )

        # Only allow alphanumeric, hyphen, and underscore
        if not re.match(r"^[a-zA-Z0-9_-]+$", theme_name):
            logger.error("Invalid theme name (invalid characters): %s", theme_name)
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                f"Invalid theme name (only alphanumeric, hyphen, underscore allowed): {theme_name}",
                ErrorContext(
                    operation="_validate_theme_name",
                    additional_data={"theme_name": theme_name},
                ),
            )

        return theme_name

    def get_qss_path(self, theme_name: str) -> Path:
        """Get the path to a theme's QSS file.

        Args:
            theme_name: Name of the theme

        Returns:
            Path to the QSS file

        Raises:
            ApplicationError: If theme file doesn't exist or invalid theme name
        """
        # Validate theme name first (security)
        theme_name = self._validate_theme_name(theme_name)

        qss_path = self.themes_dir / f"{theme_name}.qss"

        if not qss_path.exists():
            logger.error("Theme file not found: %s", qss_path)
            raise ApplicationError(
                ErrorCode.FILE_NOT_FOUND,
                f"Theme file not found: {qss_path}",
                ErrorContext(file_path=str(qss_path)),
            )

        return qss_path

    def _validate_import_path(self, qss_path: Path) -> Path:
        """Validate QSS import path for security.

        Ensures the path is within the themes directory to prevent
        directory traversal attacks.

        Args:
            qss_path: Path to validate

        Returns:
            Resolved absolute path

        Raises:
            ApplicationError: If path is outside allowed directory
        """
        # Resolve to absolute path
        resolved_path = qss_path.resolve()
        themes_dir_resolved = self.themes_dir.resolve()

        # Check if path is within themes directory
        try:
            if resolved_path.is_relative_to(themes_dir_resolved):
                logger.debug("Import path validated: %s", resolved_path)
                return resolved_path
        except (ValueError, AttributeError):
            pass

        # Path is outside allowed directory
        logger.error("Import path outside themes directory: %s", resolved_path)
        raise ApplicationError(
            ErrorCode.VALIDATION_ERROR,
            f"QSS import path outside themes directory: {qss_path}",
            ErrorContext(
                operation="_validate_import_path",
                additional_data={
                    "requested_path": str(qss_path),
                    "resolved_path": str(resolved_path),
                    "allowed_dir": str(themes_dir_resolved),
                },
            ),
        )

    def _read_file_with_imports(
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
        if len(visited) >= MAX_IMPORT_DEPTH:
            logger.error("Max import depth exceeded: %d", len(visited))
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                f"Max QSS import depth exceeded ({MAX_IMPORT_DEPTH})",
                ErrorContext(
                    operation="_read_file_with_imports",
                    additional_data={"depth": len(visited)},
                ),
            )

        # Validate and resolve path
        resolved_path = self._validate_import_path(qss_path)

        # Check for circular imports
        if resolved_path in visited:
            logger.error("Circular QSS import detected: %s", resolved_path)
            visited_str = ", ".join(str(p) for p in visited)
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                f"Circular QSS import detected: {resolved_path}",
                ErrorContext(
                    operation="_read_file_with_imports",
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

                    logger.debug(
                        "Processing QSS import: %s -> %s", import_path, nested_path
                    )

                    # Recursively read imported file
                    imported_content = self._read_file_with_imports(
                        nested_path, visited
                    )
                    lines.append(imported_content)
                else:
                    # Regular line, keep as-is
                    lines.append(line)

            return "\n".join(lines)

        except FileNotFoundError as e:
            logger.exception("QSS import file not found: %s", resolved_path)
            raise ApplicationError(
                ErrorCode.FILE_NOT_FOUND,
                f"QSS import file not found: {resolved_path}",
                ErrorContext(
                    operation="_read_file_with_imports",
                    file_path=str(resolved_path),
                ),
            ) from e
        except Exception as e:
            logger.exception("Failed to read QSS file with imports: %s", resolved_path)
            raise ApplicationError(
                ErrorCode.FILE_READ_ERROR,
                f"Failed to read QSS file with imports: {resolved_path}: {e}",
                ErrorContext(
                    operation="_read_file_with_imports",
                    file_path=str(resolved_path),
                ),
            ) from e

    def load_theme_content(self, theme_name: str) -> str:
        """Load QSS content from a theme file with @import resolution.

        Resolves @import directives recursively and includes circular
        import detection and path security validation.

        Args:
            theme_name: Name of the theme to load

        Returns:
            QSS content as string with all imports resolved

        Raises:
            ApplicationError: If theme file cannot be read
        """
        qss_path = None
        try:
            qss_path = self.get_qss_path(theme_name)

            # Use cached @import-aware reader (mtime-based)
            content = self._get_cached_theme(qss_path)

            logger.debug("Loaded theme content for: %s (with imports)", theme_name)
            return content

        except Exception as e:
            logger.exception("Failed to load theme content for %s", theme_name)
            raise ApplicationError(
                ErrorCode.FILE_READ_ERROR,
                f"Failed to load theme content for {theme_name}: {e}",
                ErrorContext(
                    file_path=str(qss_path) if qss_path else f"{theme_name}.qss",
                ),
            ) from e

    def _get_cached_theme(self, path: Path) -> str:
        """Get theme content from cache or load and cache it.

        Implements mtime-based cache validation:
        - Cache hit: If mtime matches, return cached content
        - Cache miss: Load content, cache with new mtime

        Args:
            path: Path to the QSS file

        Returns:
            QSS content as string

        Raises:
            ApplicationError: If file cannot be read
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
        cached = self._qss_cache.get(path)
        if cached and cached[0] == mtime_ns:
            logger.debug("Cache hit for theme: %s", path.name)
            return cached[1]

        # Cache miss - load and cache
        logger.debug("Cache miss for theme: %s (loading)", path.name)
        content = self._read_file_with_imports(path)
        self._qss_cache[path] = (mtime_ns, content)

        return content

    def apply_theme(
        self,
        theme_name: str,
        app: QApplication | None = None,
        _fallback_attempted: bool = False,
    ) -> None:
        """Apply a theme with automatic fallback and recursion prevention.

        Implements 3-level fallback strategy:
        - Level 1: Try requested theme
        - Level 2: On failure, try DEFAULT_THEME (light) if different
        - Level 3: On failure, apply empty stylesheet (safe mode)

        Args:
            theme_name: Name of the theme to apply
            app: QApplication instance (None = auto-detect)
            _fallback_attempted: Internal flag to prevent infinite recursion
                                (DO NOT SET MANUALLY)

        Raises:
            ApplicationError: If theme cannot be applied and all fallbacks fail
        """
        # Validate theme name (security)
        theme_name = self._validate_theme_name(theme_name)

        # Get QApplication instance
        if app is None:
            app = QApplication.instance()

        if app is None:
            logger.error("No QApplication instance found")
            raise ApplicationError(
                ErrorCode.APPLICATION_ERROR,
                "No QApplication instance found",
                ErrorContext(operation="apply_theme"),
            )

        # Level 1: Try requested theme
        try:
            logger.info("Applying theme: %s", theme_name)

            # Load theme content
            qss_content = self.load_theme_content(theme_name)

            # Apply to application
            # 1) 이전 스타일 제거 + 플랫폼 기본 팔레트로 리셋
            app.setStyleSheet("")
            app.setPalette(app.style().standardPalette())

            # 2) 새 스타일 적용
            app.setStyleSheet(qss_content)
            self.current_theme = theme_name

            # 3) 위젯 리폴리시 (툴바/메뉴/상태바까지 강제 반영)
            self._repolish_all_top_levels(app)

            logger.info("Successfully applied theme: %s", theme_name)
            return  # Success!

        except Exception as e:  # noqa: BLE001
            logger.warning(
                "Failed to apply theme %s: %s",
                theme_name,
                e,
                exc_info=True,
            )

            # Level 2: Fallback to default theme (if not already trying default)
            if not _fallback_attempted and theme_name != self.DEFAULT_THEME:
                logger.warning(
                    "Falling back to default theme: %s",
                    self.DEFAULT_THEME,
                )
                try:
                    # Recursive call with fallback flag
                    self.apply_theme(
                        self.DEFAULT_THEME,
                        app=app,
                        _fallback_attempted=True,
                    )
                    return  # Fallback success!
                except Exception:
                    logger.exception(
                        "Failed to apply fallback theme %s",
                        self.DEFAULT_THEME,
                    )

            # Level 3: Safe mode - apply empty stylesheet
            logger.error(  # noqa: TRY400
                "All theme loading failed. Entering safe mode (empty stylesheet)."
            )
            try:
                app.setStyleSheet("")
                app.setPalette(app.style().standardPalette())
                self._repolish_all_top_levels(app)
                self.current_theme = None  # No theme applied
                logger.warning("Safe mode activated: using default system styles")
                # Don't raise error in safe mode - allow app to continue
                return
            except Exception as safe_mode_error:  # noqa: BLE001
                # Safe mode also failed - this is critical
                logger.critical(
                    "Safe mode failed: %s",
                    safe_mode_error,
                    exc_info=True,
                )
                raise ApplicationError(
                    ErrorCode.APPLICATION_ERROR,
                    f"Failed to apply theme and all fallbacks: {e}",
                    ErrorContext(
                        operation="apply_theme",
                        additional_data={
                            "requested_theme": theme_name,
                            "fallback_theme": self.DEFAULT_THEME,
                            "safe_mode": True,
                        },
                    ),
                ) from e

    def _repolish_all_top_levels(self, app: QApplication) -> None:
        """Repolish all top-level widgets to ensure theme changes are applied."""
        for widget in app.topLevelWidgets():
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def get_current_theme(self) -> str | None:
        """Get the currently applied theme.

        Returns:
            Name of current theme, or None if no theme applied
        """
        return self.current_theme

    def refresh_theme_cache(self, theme_name: str | None = None) -> None:
        """Invalidate and refresh theme cache.

        This is a manual cache invalidation method for development/debugging.
        Normal theme operations automatically handle cache invalidation via
        mtime-based validation.

        Args:
            theme_name: Specific theme to refresh, or None for all themes

        Usage:
            # Development: Clear all cache after editing QSS files
            theme_manager.refresh_theme_cache()

            # Clear specific theme cache
            theme_manager.refresh_theme_cache("dark")

        Notes:
            - This is a PUBLIC method for power users and development tools
            - NOT exposed in GUI menu (internal/dev feature)
            - Can be called from CLI debug mode or test fixtures
            - Automatic mtime validation usually makes this unnecessary
        """
        if theme_name is None:
            # Clear entire cache
            count = len(self._qss_cache)
            self._qss_cache.clear()
            logger.debug("Cleared entire theme cache (%d entries)", count)
        else:
            # Validate theme name
            theme_name = self._validate_theme_name(theme_name)

            # Clear specific theme entries
            # Match by Path.stem (filename without extension)
            to_remove = [
                path
                for path in self._qss_cache
                if path.stem == theme_name or path.name == f"{theme_name}.qss"
            ]

            for path in to_remove:
                del self._qss_cache[path]

            logger.debug(
                "Cleared cache for theme '%s' (%d entries)",
                theme_name,
                len(to_remove),
            )

    def load_and_apply_theme(self, app: QApplication, theme_name: str) -> None:
        """Load and apply a theme to the application.

        .. deprecated:: 0.1.0
            Use :meth:`apply_theme` instead. This method is a compatibility
            wrapper that delegates to the new unified apply_theme method.

        Args:
            app: QApplication instance
            theme_name: Name of the theme to load and apply
        """
        import warnings

        warnings.warn(
            "load_and_apply_theme is deprecated, use apply_theme instead",
            DeprecationWarning,
            stacklevel=2,
        )
        # Delegate to new unified method
        self.apply_theme(theme_name, app=app)
