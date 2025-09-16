"""Main entry point for AniVault application."""

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from .app import AniVaultApp


def main() -> int:
    """Main entry point for the application."""
    # Enable High DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("AniVault")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("AniVault")

    # Create and show main window
    main_window = AniVaultApp()
    main_window.show()

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
