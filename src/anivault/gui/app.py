"""
Main GUI Application Entry Point

This module contains the main application class that initializes
and runs the AniVault GUI application.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import toml
from PySide6.QtWidgets import QApplication

from anivault.config import get_config, load_settings
from anivault.config.auto_scanner import AutoScanner
from anivault.containers import Container
from anivault.shared.error_handling import (
    create_error_context,
    map_exception_to_anivault_error,
)
from anivault.shared.errors import (
    AniVaultError,
    AniVaultFileError,
    AniVaultParsingError,
    ApplicationError,
    ErrorCode,
    ErrorContextModel,
)

from .main_window import MainWindow
from .themes import ThemeManager

logger = logging.getLogger(__name__)

# Global DI container instance
_container: Container | None = None


def get_container() -> Container:
    """Get or create the DI container instance.

    Returns:
        Container instance for dependency injection
    """
    global _container  # pylint: disable=global-statement
    if _container is None:
        _container = Container()
        # Wire modules that use DI
        _container.wire(
            modules=[
                "anivault.gui.workers.tmdb_matching_worker",
            ]
        )
        logger.debug("DI container initialized and wired for GUI")
    return _container


class AniVaultGUI:
    """Main GUI application class."""

    def __init__(self) -> None:
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
            # Initialize DI container first
            get_container()

            # Create QApplication
            self.app = QApplication(sys.argv)
            self.app.setApplicationName("AniVault")
            self.app.setApplicationVersion("1.0.0")
            self.app.setOrganizationName("AniVault")

            # High DPI scaling is enabled by default in Qt6
            # No need to set deprecated attributes

            # Load configuration (validates and caches globally)
            # Create default config if it doesn't exist
            self._ensure_config_exists()
            load_settings(self.config_path)
            logger.info("Successfully loaded and validated configuration")

            # Initialize auto scanner
            self.auto_scanner = AutoScanner(self.config_path)

            # Initialize theme manager
            self.theme_manager = ThemeManager()

            # Create main window BEFORE applying theme
            # (theme application requires existing widgets to repolish)
            self.main_window = MainWindow()

            # Set theme manager in main window
            self.main_window.set_theme_manager(self.theme_manager)

            # Load and apply initial theme AFTER window creation
            if self.theme_manager:
                self._load_initial_theme()

            # Setup auto scanner callback
            self._setup_auto_scanner()

            logger.info("GUI application initialized successfully")
            return True

        except (OSError, PermissionError) as e:
            # File I/O errors during initialization - use common error mapping
            error = map_exception_to_anivault_error(
                e,
                "gui_initialization",
                default_code=ErrorCode.FILE_ACCESS_ERROR,
            )
            # Convert to AniVaultFileError for specific error type
            if not isinstance(error, AniVaultFileError):
                context = create_error_context("gui_initialization")
                error = AniVaultFileError(
                    ErrorCode.FILE_ACCESS_ERROR,
                    f"File I/O error during GUI initialization: {e}",
                    context,
                    original_error=e,
                )
            logger.exception("Failed to initialize GUI application: %s", error.message)
            return False
        except (ValueError, AttributeError) as e:
            # Configuration/data structure errors - use common error mapping
            error = map_exception_to_anivault_error(
                e,
                "gui_initialization",
                default_code=ErrorCode.CONFIGURATION_ERROR,
            )
            # Convert to AniVaultParsingError for specific error type
            if not isinstance(error, AniVaultParsingError):
                context = create_error_context("gui_initialization")
                error = AniVaultParsingError(
                    ErrorCode.CONFIGURATION_ERROR,
                    f"Configuration error during GUI initialization: {e}",
                    context,
                    original_error=e,
                )
            logger.exception("Failed to initialize GUI application: %s", error.message)
            return False
        # pylint: disable-next=broad-exception-caught

        # pylint: disable-next=broad-exception-caught

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Unexpected errors during initialization - use common error mapping
            error = map_exception_to_anivault_error(
                e,
                "gui_initialization",
                default_code=ErrorCode.APPLICATION_ERROR,
            )
            logger.exception("Failed to initialize GUI application: %s", error.message)
            return False

    def _ensure_config_exists(self) -> None:
        """Ensure config file exists, create default if missing."""
        try:
            # Check if config file exists
            if not self.config_path.exists():
                logger.info("Config file not found, creating default configuration")

                # Ensure config directory exists
                self.config_path.parent.mkdir(parents=True, exist_ok=True)

                # Create default config file
                self._create_default_config()
                logger.info("Default configuration created successfully")
            else:
                logger.info("Config file found, using existing configuration")

        except (OSError, PermissionError) as e:
            # File I/O errors during config creation
            context = ErrorContextModel(
                file_path=str(self.config_path),
                operation="ensure_config_exists",
            )
            error = AniVaultFileError(
                ErrorCode.FILE_CREATE_ERROR,
                f"Failed to ensure config exists: {e}",
                context,
                original_error=e,
            )
            logger.exception("Failed to ensure config exists: %s", error.message)
            raise error from e
        # pylint: disable-next=broad-exception-caught

        # pylint: disable-next=broad-exception-caught

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Unexpected errors during config creation
            context = ErrorContextModel(
                file_path=str(self.config_path),
                operation="ensure_config_exists",
            )
            config_error = AniVaultError(
                ErrorCode.CONFIGURATION_ERROR,
                f"Unexpected error ensuring config exists: {e}",
                context,
                original_error=e,
            )
            logger.exception("Failed to ensure config exists: %s", config_error.message)
            raise config_error from e

    def _create_default_config(self) -> None:
        """Create default configuration file."""

        default_config = {
            "app": {
                "name": "AniVault",
                "version": "0.1.0",
                "debug": False,
                "theme": "dark",
            },
            "logging": {"level": "INFO", "format": "text"},
            "tmdb": {"language": "ko-KR", "region": "KR"},
            "file_processing": {"max_workers": 4, "batch_size": 50},
            "cache": {
                "enabled": True,
                "ttl_seconds": 604800,  # 7 days
            },
        }

        # Write config file
        with open(self.config_path, "w", encoding="utf-8") as f:
            toml.dump(default_config, f)

        logger.info("Default config file created at: %s", self.config_path)

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
            exit_code: int = self.app.exec()
            return exit_code

        except (KeyboardInterrupt, SystemExit):  # pylint: disable=try-except-raise
            # Expected termination signals - re-raise
            raise
        # pylint: disable-next=broad-exception-caught

        # pylint: disable-next=broad-exception-caught

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Unexpected errors during application execution
            context = ErrorContextModel(operation="gui_application_run")
            run_error = AniVaultError(
                ErrorCode.APPLICATION_ERROR,
                f"Error running GUI application: {e}",
                context,
                original_error=e,
            )
            logger.exception("Error running GUI application: %s", run_error.message)
            return 1

    def _load_initial_theme(self) -> None:
        """Load and apply the initial theme from configuration."""
        try:
            # Get saved theme from configuration

            config = get_config()
            saved_theme = config.app.theme

            # Apply the theme (app parameter is optional, auto-detected)
            if self.theme_manager is not None:
                self.theme_manager.apply_theme(saved_theme, app=self.app)

            logger.info("Initial theme loaded: %s", saved_theme)

        except ApplicationError:
            # ApplicationError already handled by apply_theme's fallback chain
            logger.exception("Theme loading failed, fallback applied")
        # pylint: disable-next=broad-exception-caught

        # pylint: disable-next=broad-exception-caught

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Unexpected errors during theme loading (fallback already applied)
            theme_name_str = saved_theme if "saved_theme" in locals() and saved_theme is not None else "unknown"
            context = ErrorContextModel(
                operation="load_initial_theme",
                additional_data={"theme": theme_name_str},
            )
            theme_error = AniVaultError(
                ErrorCode.APPLICATION_ERROR,
                f"Unexpected error loading theme: {e}",
                context,
                original_error=e,
            )
            logger.exception("Theme loading failed, fallback applied: %s", theme_error.message)

    def _setup_auto_scanner(self) -> None:
        """Setup auto scanner with callback to main window."""
        if self.auto_scanner is not None and self.main_window is not None:
            # Set callback to trigger scanning in main window
            main_window = self.main_window  # Local reference for type narrowing

            def scan_callback(folder_path: str) -> None:
                """Callback function for auto scanning."""
                try:
                    logger.info("Auto scan triggered for folder: %s", folder_path)
                    # Set directory in state model and start scanning
                    if main_window is not None and main_window.state_model is not None:
                        main_window.state_model.selected_directory = Path(folder_path)
                        main_window.start_file_scan()
                except (OSError, PermissionError) as e:
                    # File I/O errors during auto scan
                    context = ErrorContextModel(
                        operation="auto_scan_callback",
                        additional_data={"folder_path": folder_path},
                    )
                    error = AniVaultFileError(
                        ErrorCode.FILE_ACCESS_ERROR,
                        f"Auto scan callback failed: {e}",
                        context,
                        original_error=e,
                    )
                    logger.exception("Auto scan callback failed: %s", error.message)
                # pylint: disable-next=broad-exception-caught

                # pylint: disable-next=broad-exception-caught

                except Exception as e:  # pylint: disable=broad-exception-caught
                    # Unexpected errors during auto scan callback
                    context = ErrorContextModel(
                        operation="auto_scan_callback",
                        additional_data={"folder_path": folder_path},
                    )
                    callback_error = AniVaultError(
                        ErrorCode.APPLICATION_ERROR,
                        f"Unexpected error in auto scan callback: {e}",
                        context,
                        original_error=e,
                    )
                    logger.exception("Auto scan callback failed: %s", callback_error.message)

            self.auto_scanner.set_scan_callback(scan_callback)

    def _check_auto_scan_startup(self) -> None:
        """Check if auto scan should be performed on startup."""
        if not self.auto_scanner:
            return

        try:
            should_scan, _source_folder = self.auto_scanner.should_auto_scan_on_startup()
            if should_scan:
                logger.info("Auto scan on startup enabled, starting scan...")
                success, message = self.auto_scanner.perform_auto_scan()
                if success:
                    logger.info("Auto scan on startup completed: %s", message)
                else:
                    logger.warning("Auto scan on startup failed: %s", message)
            else:
                logger.info("Auto scan on startup not enabled or configured")
        except ApplicationError:
            # ApplicationError from should_auto_scan_on_startup provides detailed context
            logger.exception("Error during auto scan startup check")
            # Continue app startup gracefully
        # pylint: disable-next=broad-exception-caught

        # pylint: disable-next=broad-exception-caught

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Unexpected errors during auto scan startup check
            context = ErrorContextModel(operation="check_auto_scan_startup")
            startup_error = AniVaultError(
                ErrorCode.APPLICATION_ERROR,
                f"Unexpected error during auto scan startup check: {e}",
                context,
                original_error=e,
            )
            logger.exception("Error during auto scan startup check: %s", startup_error.message)
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
                    self.main_window.tmdb_controller._cleanup_matching_thread()  # pylint: disable=protected-access

            # Quit application
            if self.app:
                self.app.quit()
                logger.info("GUI application cleaned up")
        # pylint: disable-next=broad-exception-caught

        # pylint: disable-next=broad-exception-caught

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Unexpected errors during cleanup - log but don't crash
            context = ErrorContextModel(operation="gui_cleanup")
            cleanup_error = AniVaultError(
                ErrorCode.APPLICATION_ERROR,
                f"Error during cleanup: {e}",
                context,
                original_error=e,
            )
            logger.exception("Error during cleanup: %s", cleanup_error.message)


def main() -> int:
    """Main entry point for GUI application.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    gui_app = AniVaultGUI()
    container = get_container()

    try:
        # Initialize application
        if not gui_app.initialize():
            return 1

        # Run application
        return gui_app.run()

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        return 0

    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception("Unexpected error")
        return 1

    finally:
        gui_app.cleanup()
        # Unwire container on cleanup
        if container:
            container.unwire()


if __name__ == "__main__":
    sys.exit(main())
