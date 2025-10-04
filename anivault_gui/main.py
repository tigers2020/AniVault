"""Main entry point for the AniVault GUI application.

This module creates the QApplication instance and launches the main window.
"""

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from anivault_gui.models.state_model import StateModel
from anivault_gui.windows.main_window import MainWindow


def main() -> int:
    """Main entry point for the AniVault GUI application.

    Returns:
        Exit code for the application
    """
    # Create QApplication instance
    app = QApplication(sys.argv)
    app.setApplicationName("AniVault")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("AniVault Team")

    # Enable high DPI scaling
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Create state model
    state_model = StateModel()

    # Create and show main window
    main_window = MainWindow(state_model)
    main_window.show()

    # Start event loop
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
