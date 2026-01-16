"""Status Bar Widget for GUI v2."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class StatusBar(QWidget):
    """Status bar widget showing system status."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize status bar widget."""
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the status bar UI."""
        self.setObjectName("statusBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 12, 32, 12)
        layout.setSpacing(32)

        # Status left section
        status_left = QHBoxLayout()
        status_left.setSpacing(16)

        # Status indicator
        status_item_layout = QHBoxLayout()
        status_item_layout.setSpacing(6)

        self.status_dot = QLabel()
        self.status_dot.setObjectName("statusDot")
        self.status_dot.setFixedSize(8, 8)
        status_item_layout.addWidget(self.status_dot)

        self.status_text = QLabel("unknown")
        status_item_layout.addWidget(self.status_text)

        status_left.addLayout(status_item_layout)

        # Current path
        path_item_layout = QHBoxLayout()
        path_item_layout.setSpacing(6)

        path_label = QLabel("🗺️")
        path_item_layout.addWidget(path_label)

        self.current_path = QLabel("unknown")
        path_item_layout.addWidget(self.current_path)

        status_left.addLayout(path_item_layout)

        layout.addLayout(status_left)
        layout.addStretch()

        # Status right section
        cache_status_layout = QHBoxLayout()
        cache_status_label = QLabel("캐시:")
        cache_status_layout.addWidget(cache_status_label)

        self.cache_status = QLabel("unknown")
        self.cache_status.setObjectName("cacheStatus")
        cache_status_layout.addWidget(self.cache_status)

        layout.addLayout(cache_status_layout)

    def set_status(self, text: str, status_type: str = "ok") -> None:
        """Update status text and indicator.

        Args:
            text: Status message
            status_type: Status type ('ok', 'warn', 'error')
        """
        self.status_text.setText(text)

        # Update dot color based on status type
        color_map = {
            "ok": "#10b981",
            "warn": "#f59e0b",
            "error": "#ef4444",
        }
        color = color_map.get(status_type, "#10b981")
        self.status_dot.setStyleSheet(f"background-color: {color};")

    def set_current_path(self, path: str) -> None:
        """Update current path display."""
        self.current_path.setText(path)

    def set_cache_status(self, status: str) -> None:
        """Update cache status display."""
        self.cache_status.setText(status)
