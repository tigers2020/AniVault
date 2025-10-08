"""
Main GUI Application Entry Point

This module contains the main application class that initializes
and runs the AniVault GUI application.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from anivault.config.auto_scanner import AutoScanner
from anivault.config.settings import load_settings, reload_config

from .main_window import MainWindow
from .themes import ThemeManager

logger = logging.getLogger(__name__)


class AniVaultGUI:
    """Main GUI application class."""

    def __init__(self):
        self.app: QApplication | None = None
        self.main_window: MainWindow | None = None
        self.theme_manager: ThemeManager | None = None
        self.auto_scanner: AutoScanner | None = None
        self.config_path: Path = Path("config/config.toml")

    def initialize(self) -> bool:
        """
        Initialize the GUI application.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Create QApplication
            self.app = QApplication(sys.argv)
            self.app.setApplicationName("AniVault")
            self.app.setApplicationVersion("1.0.0")
            self.app.setOrganizationName("AniVault")

            # High DPI scaling is enabled by default in Qt6
            # No need to set deprecated attributes

            # Load configuration (validates and caches globally)
            load_settings(self.config_path)
            logger.info("Successfully loaded and validated configuration")

            # Initialize auto scanner
            self.auto_scanner = AutoScanner(self.config_path)

            # Initialize theme manager
            self.theme_manager = ThemeManager()

            # Load and apply initial theme
            self._load_initial_theme()

            # Create main window
            self.main_window = MainWindow()

            # Set theme manager in main window
            self.main_window.set_theme_manager(self.theme_manager)

            # Setup auto scanner callback
            self._setup_auto_scanner()

            logger.info("GUI application initialized successfully")
            return True

        except Exception:
            logger.exception("Failed to initialize GUI application: %s")
            return False

    def run(self) -> int:
        """
        Run the GUI application.

        Returns:
            Exit code
        """
        if not self.app or not self.main_window:
            logger.error("Application not properly initialized")
            return 1

        try:
            # Show main window
            self.main_window.show()

            logger.info("Starting GUI application event loop")

            # Check for auto scan on startup
            self._check_auto_scan_startup()

            # Run event loop
            return self.app.exec()

        except Exception:
            logger.exception("Error running GUI application: %s")
            return 1

    def _load_initial_theme(self) -> None:
        """Load and apply the initial theme from configuration."""
        try:
            # Get saved theme from configuration
            from anivault.config.settings import get_config
            
            config = get_config()
            saved_theme = config.app.theme

            # Apply the theme
            self.theme_manager.load_and_apply_theme(self.app, saved_theme)

            logger.info("Initial theme loaded: %s", saved_theme)

        except Exception as e:
            logger.warning("Failed to load initial theme, using default: %s", e)
            # Fallback to default theme
            try:
                self.theme_manager.load_and_apply_theme(
                    self.app,
                    ThemeManager.DEFAULT_THEME,
                )
            except Exception:
                logger.exception("Failed to apply fallback theme")

    def _setup_auto_scanner(self) -> None:
        """Setup auto scanner with callback to main window."""
        if self.auto_scanner and self.main_window:
            # Set callback to trigger scanning in main window
            def scan_callback(folder_path: str) -> None:
                """Callback function for auto scanning."""
                try:
                    logger.info("Auto scan triggered for folder: %s", folder_path)
                    # Set directory in state model and start scanning
                    self.main_window.state_model.selected_directory = Path(folder_path)
                    self.main_window.start_file_scan()
                except Exception:
                    logger.exception("Auto scan callback failed: %s")

            self.auto_scanner.set_scan_callback(scan_callback)

    def _check_auto_scan_startup(self) -> None:
        """Check if auto scan should be performed on startup."""
        if not self.auto_scanner:
            return

        try:
            should_scan, _source_folder = (
                self.auto_scanner.should_auto_scan_on_startup()
            )
            if should_scan:
                logger.info("Auto scan on startup enabled, starting scan...")
                success, message = self.auto_scanner.perform_auto_scan()
                if success:
                    logger.info("Auto scan on startup completed: %s", message)
                else:
                    logger.warning("Auto scan on startup failed: %s", message)
            else:
                logger.info("Auto scan on startup not enabled or configured")
        except Exception:
            # ApplicationError from should_auto_scan_on_startup provides detailed context
            logger.exception("Error during auto scan startup check")
            # Continue app startup gracefully

    def cleanup(self) -> None:
        """Clean up application resources."""
        try:
            # Clean up controllers and threads first
            if self.main_window:
                # Ensure all threads are properly cleaned up
                if hasattr(self.main_window, "scan_controller"):
                    # ScanController doesn't have _cleanup_scanning_thread method
                    # Thread cleanup is handled in _start_scanning_thread
                    pass
                if hasattr(self.main_window, "tmdb_controller"):
                    self.main_window.tmdb_controller._cleanup_matching_thread()

            # Quit application
            if self.app:
                self.app.quit()
                logger.info("GUI application cleaned up")
        except Exception:
            logger.exception("Error during cleanup: %s")


def main() -> int:
    """Main entry point for GUI application."""
    gui_app = AniVaultGUI()

    try:
        # Initialize application
        if not gui_app.initialize():
            return 1

        # Run application
        return gui_app.run()

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        return 0

    except Exception:
        logger.exception("Unexpected error: %s")
        return 1

    finally:
        gui_app.cleanup()


if __name__ == "__main__":
    sys.exit(main())
