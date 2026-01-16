"""Loading Overlay Widget for GUI v2."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class LoadingOverlay(QWidget):
    """Loading overlay widget displayed during operations."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize loading overlay widget."""
        super().__init__(parent)
        self.setObjectName("loadingOverlay")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._setup_ui()
        self.hide()

    def _setup_ui(self) -> None:
        """Set up the loading overlay UI."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Loading content container
        content = QWidget()
        content.setObjectName("loadingContent")
        content_layout = QVBoxLayout(content)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.setSpacing(16)
        content_layout.setContentsMargins(32, 32, 32, 32)

        # Spinner (using Unicode character as placeholder)
        spinner_label = QLabel("⟳")
        spinner_label.setObjectName("loadingSpinner")
        content_layout.addWidget(spinner_label)

        # Message
        self.message_label = QLabel("처리 중...")
        self.message_label.setObjectName("loadingMessage")
        content_layout.addWidget(self.message_label)

        layout.addWidget(content)

    def show_loading(self, message: str = "처리 중...") -> None:
        """Show loading overlay with message.

        Args:
            message: Loading message to display
        """
        if self.parent():
            parent = self.parent()
            self.setGeometry(0, 0, parent.width(), parent.height())
        self.message_label.setText(message)
        self.show()
        self.raise_()

    def hide_loading(self) -> None:
        """Hide loading overlay."""
        self.hide()
