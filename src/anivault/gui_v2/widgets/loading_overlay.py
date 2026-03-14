"""Loading Overlay Widget for GUI v2."""

from __future__ import annotations

from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget


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

        # Progress bar (hidden when total is 0 or not set)
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("loadingProgressBar")
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        content_layout.addWidget(self.progress_bar)

        layout.addWidget(content)

    def show_loading(
        self,
        message: str = "처리 중...",
        current: int | None = None,
        total: int | None = None,
    ) -> None:
        """Show loading overlay with message and optional progress.

        Args:
            message: Loading message to display.
            current: Current progress count (used when total > 0).
            total: Total count; when > 0, progress bar and percent are shown.
        """
        if self.parent():
            parent = cast("QWidget", self.parent())
            self.setGeometry(0, 0, parent.width(), parent.height())

        if total is not None and total > 0 and current is not None:
            pct = round(100 * current / total)
            display_message = f"{message} ({pct}%)"
            self.message_label.setText(display_message)
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(min(current, total))
            self.progress_bar.show()
        else:
            self.message_label.setText(message)
            self.progress_bar.hide()

        self.show()
        self.raise_()

    def hide_loading(self) -> None:
        """Hide loading overlay."""
        self.progress_bar.hide()
        self.hide()
