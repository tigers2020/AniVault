"""Main entry point for AniVault application."""

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from .app import AniVaultApp
from .utils.logger import get_logger, setup_logging


def main() -> int:
    """Main entry point for the application."""
    # Set up logging first
    log_manager = setup_logging()
    logger = get_logger(__name__)

    logger.info("Starting AniVault application")

    try:
        # Enable High DPI scaling
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        app = QApplication(sys.argv)
        app.setApplicationName("AniVault")
        app.setApplicationVersion("0.1.0")
        app.setOrganizationName("AniVault")

        logger.info("QApplication created successfully")

        # Apply global dark theme to QApplication
        from .themes.theme_manager import get_theme_manager

        theme_manager = get_theme_manager()
        app.setStyleSheet(theme_manager.current_theme.get_complete_style())
        logger.info("Theme applied successfully")

        # Create and show main window
        main_window = AniVaultApp()
        main_window.show()
        logger.info("Main window created and shown")

        # Run application
        result = int(app.exec_())
        logger.info(f"Application exited with code {result}")
        return result

    except Exception as e:
        logger.critical(f"Fatal error in main: {e}", exc_info=True)
        return 1
    finally:
        # Clean up logging
        log_manager.cleanup()


if __name__ == "__main__":
    sys.exit(main())
