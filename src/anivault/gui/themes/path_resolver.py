"""
Theme Path Resolver for AniVault GUI

This module provides path resolution and management for theme files,
including PyInstaller bundle mode detection, theme directory setup,
and secure path masking for logging.
"""

from __future__ import annotations

import logging
import shutil
import sys
from pathlib import Path
from typing import ClassVar

from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext

from .theme_validator import ThemeValidator

logger = logging.getLogger(__name__)


class ThemePathResolver:
    """Resolves and manages theme file paths across different environments.

    This class handles:
    - PyInstaller bundle vs development mode detection
    - Theme directory initialization (user-writable + bundle resources)
    - Theme file path resolution with fallback priority
    - Bundle theme file copying to user directory
    - Secure path masking for logging (hides home directory)

    Path Resolution Priority (Bundle Mode):
        1. User theme directory (~/.anivault/themes) - writable
        2. Bundle base directory (PyInstaller resources) - read-only
        3. Fallback to default theme (light.qss)
        4. Return None if all searches fail
    """

    # Required theme files for bundle initialization
    REQUIRED_THEME_FILES: ClassVar[list[str]] = [
        "light.qss",
        "dark.qss",
        "common.qss",
    ]

    # Default theme for fallback
    LIGHT_THEME: ClassVar[str] = "light"

    def __init__(
        self,
        themes_dir: Path | None,
        validator: ThemeValidator,
    ) -> None:
        """Initialize path resolver with theme directories.

        Args:
            themes_dir: Optional path to themes directory. If None, uses
                       default path based on environment (bundle/development)
            validator: ThemeValidator instance for theme name validation
        """
        self._validator = validator

        # Detect PyInstaller bundle environment
        self._is_bundled = hasattr(sys, "_MEIPASS")

        if themes_dir is None:
            if self._is_bundled:
                # PyInstaller bundle: read-only embedded resources
                self.base_theme_dir = (
                    Path(sys._MEIPASS) / "resources" / "themes"  # type: ignore[attr-defined]
                )
                # User-writable directory for theme files
                self.user_theme_dir = Path.home() / ".anivault" / "themes"
                # Use user directory as primary themes_dir
                self.themes_dir = self.user_theme_dir
            else:
                # Development: package-relative path
                package_dir = Path(__file__).parent.parent.parent
                self.themes_dir = package_dir / "resources" / "themes"
                # In development, base and user are the same
                self.base_theme_dir = self.themes_dir
                self.user_theme_dir = self.themes_dir
        else:
            self.themes_dir = Path(themes_dir)
            self.base_theme_dir = self.themes_dir
            self.user_theme_dir = self.themes_dir

        # Ensure themes directory exists
        self._ensure_themes_directory()

    @property
    def is_bundled(self) -> bool:
        """Check if running in PyInstaller bundle mode."""
        return self._is_bundled

    def get_available_themes(self) -> list[str]:
        """Get list of available theme names.

        Returns:
            List of available theme names (QSS file stems)
        """
        themes = []
        try:
            for qss_file in self.themes_dir.glob("*.qss"):
                themes.append(qss_file.stem)
            logger.debug("Available themes: %s", themes)
            return themes
        except Exception:
            logger.exception("Failed to get available themes")
            return []

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

    def ensure_bundle_themes(self) -> None:
        """Copy required theme files from bundle to user directory if missing.

        This method is only called when running as a PyInstaller bundle.
        It ensures that all required theme files exist in the user-writable
        directory by copying them from the read-only bundle resources.

        Does not raise exceptions - logs errors and continues to allow
        the application to run with potentially incomplete themes.
        """
        for theme_file_name in self.REQUIRED_THEME_FILES:
            target = self.user_theme_dir / theme_file_name
            source = self.base_theme_dir / theme_file_name

            # Skip if file already exists
            if target.exists():
                logger.debug(
                    "Theme file already exists, skipping: %s",
                    theme_file_name,
                )
                continue

            # Copy theme file from bundle to user directory
            try:
                shutil.copy2(source, target)
                logger.info(
                    "Copied bundle theme file to user directory: %s -> %s",
                    source,
                    target,
                )
            except PermissionError as e:
                logger.warning(
                    "Permission denied copying theme file: %s (source: %s, target: %s)",
                    e,
                    source,
                    target,
                    extra=ErrorContext(
                        file_path=str(target),
                        additional_data={
                            "source_path": str(source),
                            "bundle_dir": str(self.base_theme_dir),
                        },
                    ).model_dump(),
                )
            except FileNotFoundError:
                logger.error(  # noqa: TRY400
                    "Source theme file not found in bundle: %s",
                    source,
                    extra=ErrorContext(
                        file_path=str(source),
                        additional_data={
                            "bundle_dir": str(self.base_theme_dir),
                            "theme_file": theme_file_name,
                        },
                    ).model_dump(),
                )
            except Exception as e:  # noqa: BLE001
                logger.error(  # noqa: TRY400
                    "Unexpected error copying theme file %s: %s",
                    theme_file_name,
                    e,
                    extra=ErrorContext(
                        file_path=str(source),
                        additional_data={
                            "target_path": str(target),
                            "bundle_dir": str(self.base_theme_dir),
                            "error_type": type(e).__name__,
                        },
                    ).model_dump(),
                )

    def mask_home_path(self, path: Path) -> str:
        """Mask home directory in path for secure logging.

        Replaces home directory with '~' to avoid exposing absolute paths
        in log files while maintaining useful debugging information.

        Args:
            path: Path to mask

        Returns:
            String path with home directory masked
        """
        try:
            # Try to make path relative to home
            home = Path.home()
            if path.is_relative_to(home):
                rel_path = path.relative_to(home)
                return f"~/{rel_path.as_posix()}"
        except (ValueError, RuntimeError):
            # Path is not relative to home or other error
            pass

        # Fallback: return path as-is (but log only filename for security)
        return str(path.name) if path.name else str(path)

    def get_qss_path(self, theme_name: str) -> Path | None:
        """Get the path to a theme's QSS file with fallback priority.

        Search priority (bundle mode):
        1. User theme directory (~/.anivault/themes)
        2. Bundle base directory (PyInstaller bundle resources)
        3. Fallback to default theme (light.qss)
        4. Return None if all searches fail

        Args:
            theme_name: Name of the theme

        Returns:
            Path to the QSS file, or None if not found after all fallbacks

        Raises:
            ApplicationError: If theme name is invalid (security)
        """
        # Validate theme name first (security)
        theme_name = self._validator.validate_theme_name(theme_name)

        # 1. Try user theme directory first (writable location)
        user_path = self.user_theme_dir / f"{theme_name}.qss"
        if user_path.exists():
            logger.debug("Found theme in user directory: %s", user_path)
            return user_path

        # Log user directory miss (info level, not error)
        logger.info(
            "Theme not found in user directory: %s",
            theme_name,
            extra=ErrorContext(
                file_path=self.mask_home_path(user_path),
                additional_data={"stage": "user-theme", "theme_name": theme_name},
            ).model_dump(),
        )

        # 2. Try bundle base directory (read-only resources)
        base_path = self.base_theme_dir / f"{theme_name}.qss"
        if base_path.exists():
            logger.debug("Found theme in bundle directory: %s", base_path)
            return base_path

        # Log bundle directory miss
        logger.warning(
            "Theme not found in bundle directory: %s",
            theme_name,
            extra=ErrorContext(
                file_path=self.mask_home_path(base_path),
                additional_data={"stage": "bundle-theme", "theme_name": theme_name},
            ).model_dump(),
        )

        # 3. Fallback to default theme (light.qss) if not already trying it
        if theme_name != self.LIGHT_THEME:
            logger.info(
                "Falling back to default theme: %s",
                self.LIGHT_THEME,
                extra=ErrorContext(
                    file_path=self.mask_home_path(base_path),
                    additional_data={
                        "stage": "bundle-theme",
                        "theme_name": theme_name,
                        "fallback": self.LIGHT_THEME,
                    },
                ).model_dump(),
            )
            # Recursive call with default theme
            return self.get_qss_path(self.LIGHT_THEME)

        # 4. Final failure: even default theme not found
        logger.error(
            "Critical: Default theme not found: %s",
            theme_name,
            extra=ErrorContext(
                file_path=self.mask_home_path(base_path),
                additional_data={"stage": "default-fallback", "theme_name": theme_name},
            ).model_dump(),
        )

        return None
