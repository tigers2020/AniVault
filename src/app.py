"""Main application class for AniVault."""

from PyQt5.QtWidgets import QMainWindow, QWidget

from .gui.main_window import MainWindow


class AniVaultApp(QMainWindow):
    """Main application window for AniVault."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the main application window."""
        super().__init__(parent)
        self.setWindowTitle("AnimeSorter")
        self.setGeometry(100, 100, 1400, 900)

        # Create the main window with all panels
        self.main_window = MainWindow()
        self.setCentralWidget(self.main_window)
