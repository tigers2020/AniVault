"""Main application class for AniVault."""


from PyQt5.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget


class AniVaultApp(QMainWindow):
    """Main application window for AniVault."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the main application window."""
        super().__init__(parent)
        self.setWindowTitle("AniVault - Anime Management")
        self.setGeometry(100, 100, 800, 600)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create layout
        layout = QVBoxLayout(central_widget)

        # Add welcome label
        welcome_label = QLabel("Welcome to AniVault!")
        welcome_label.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px;")
        layout.addWidget(welcome_label)

        # TODO: Add main application components here
