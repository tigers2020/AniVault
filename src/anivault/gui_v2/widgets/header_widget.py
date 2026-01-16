"""Header Widget for GUI v2."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class HeaderWidget(QWidget):
    """Header widget with logo and action buttons."""

    # Signals
    settings_clicked = Signal()
    scan_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize header widget."""
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the header UI."""
        self.setObjectName("header")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 20, 32, 20)

        # Logo section
        logo_layout = QHBoxLayout()
        logo_layout.setSpacing(12)

        # Logo icon
        logo_icon = QLabel("📁")
        logo_icon.setObjectName("logoIcon")
        logo_layout.addWidget(logo_icon)

        # Logo text
        logo_text = QLabel("AniVault")
        logo_text.setObjectName("logoText")
        logo_layout.addWidget(logo_text)

        # Version label
        version_label = QLabel("v2.0.0")
        version_label.setObjectName("versionLabel")
        logo_layout.addWidget(version_label)

        layout.addLayout(logo_layout)
        layout.addStretch()

        # Action buttons
        settings_btn = QPushButton("⚙️ 설정")
        settings_btn.setObjectName("btnSecondary")
        settings_btn.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(settings_btn)

        scan_btn = QPushButton("📂 디렉터리 스캔")
        scan_btn.setObjectName("btnPrimary")
        scan_btn.clicked.connect(self.scan_clicked.emit)
        layout.addWidget(scan_btn)
