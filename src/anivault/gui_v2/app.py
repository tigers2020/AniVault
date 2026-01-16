"""AniVault GUI v2 Application Entry Point."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from anivault.gui_v2.app_context import AppContext
from anivault.gui_v2.main_window import MainWindow
from anivault.gui_v2.styles.styles import StyleManager

logger = logging.getLogger(__name__)


class AniVaultGUIv2:
    """Main GUI v2 application class."""

    def __init__(self) -> None:
        """Initialize GUI v2 application."""
        self.app: QApplication | None = None
        self.main_window: MainWindow | None = None
        self.style_manager: StyleManager | None = None
        self.app_context: AppContext | None = None

    def initialize(self) -> bool:
        """
        Initialize the GUI v2 application.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Create QApplication
            self.app = QApplication(sys.argv)
            self.app.setApplicationName("AniVault")
            self.app.setApplicationVersion("2.0.0")
            self.app.setOrganizationName("AniVault")

            # Initialize shared application context
            self.app_context = AppContext()

            # Initialize style manager with dark theme
            self.style_manager = StyleManager(theme=StyleManager.DARK_THEME)

            # Create main window
            self.main_window = MainWindow(app_context=self.app_context)

            # Apply styles
            if self.style_manager:
                self.style_manager.apply_styles(self.app)

            logger.info("GUI v2 application initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize GUI v2: {e}", exc_info=True)
            return False

    def run(self) -> int:
        """
        Run the GUI application.

        Returns:
            Application exit code
        """
        if not self.app or not self.main_window:
            logger.error("Application not initialized. Call initialize() first.")
            return 1

        self.main_window.show()
        return self.app.exec()


def main() -> int:
    """Main entry point for GUI v2."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    app = AniVaultGUIv2()
    if not app.initialize():
        return 1

    return app.run()


if __name__ == "__main__":
    sys.exit(main())
