"""Work panel for file operations and controls."""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class WorkPanel(QGroupBox):
    """Work panel containing source/target folders and action buttons."""

    scan_requested = pyqtSignal()
    organize_requested = pyqtSignal()
    preview_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        """Initialize the work panel."""
        super().__init__("작업 패널", parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Source folder section
        source_layout = QVBoxLayout()
        source_label = QLabel("소스 폴더")
        source_label.setStyleSheet("font-weight: bold; color: #94a3b8;")

        self.source_path_edit = QLineEdit()
        self.source_path_edit.setPlaceholderText("소스 경로를 선택하세요...")
        self.source_path_edit.setStyleSheet(
            """
            QLineEdit {
                background-color: #334155;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 8px;
                color: #f1f5f9;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
            }
        """
        )

        source_browse_btn = QPushButton("찾아보기")
        source_browse_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #475569;
                border: 1px solid #64748b;
                border-radius: 6px;
                padding: 6px 12px;
                color: #f1f5f9;
            }
            QPushButton:hover {
                background-color: #64748b;
            }
            QPushButton:pressed {
                background-color: #334155;
            }
        """
        )
        source_browse_btn.clicked.connect(self._browse_source_folder)

        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source_path_edit)
        source_layout.addWidget(source_browse_btn)

        # Target folder section
        target_layout = QVBoxLayout()
        target_label = QLabel("대상 폴더")
        target_label.setStyleSheet("font-weight: bold; color: #94a3b8;")

        self.target_path_edit = QLineEdit()
        self.target_path_edit.setPlaceholderText("대상 경로를 선택하세요...")
        self.target_path_edit.setStyleSheet(
            """
            QLineEdit {
                background-color: #334155;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 8px;
                color: #f1f5f9;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
            }
        """
        )

        target_browse_btn = QPushButton("찾아보기")
        target_browse_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #475569;
                border: 1px solid #64748b;
                border-radius: 6px;
                padding: 6px 12px;
                color: #f1f5f9;
            }
            QPushButton:hover {
                background-color: #64748b;
            }
            QPushButton:pressed {
                background-color: #334155;
            }
        """
        )
        target_browse_btn.clicked.connect(self._browse_target_folder)

        target_layout.addWidget(target_label)
        target_layout.addWidget(self.target_path_edit)
        target_layout.addWidget(target_browse_btn)

        # Action buttons
        buttons_layout = QHBoxLayout()

        self.scan_btn = QPushButton("스캔")
        self.scan_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #3b82f6;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """
        )
        self.scan_btn.clicked.connect(self.scan_requested.emit)

        self.organize_btn = QPushButton("정리")
        self.organize_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #10b981;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
        """
        )
        self.organize_btn.clicked.connect(self.organize_requested.emit)

        self.preview_btn = QPushButton("미리보기")
        self.preview_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #8b5cf6;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7c3aed;
            }
            QPushButton:pressed {
                background-color: #6d28d9;
            }
        """
        )
        self.preview_btn.clicked.connect(self.preview_requested.emit)

        buttons_layout.addWidget(self.scan_btn)
        buttons_layout.addWidget(self.organize_btn)
        buttons_layout.addWidget(self.preview_btn)

        # Add all sections to main layout
        layout.addLayout(source_layout)
        layout.addLayout(target_layout)
        layout.addLayout(buttons_layout)
        layout.addStretch()

    def _browse_source_folder(self) -> None:
        """Browse for source folder."""
        folder = QFileDialog.getExistingDirectory(self, "소스 폴더 선택", "")
        if folder:
            self.source_path_edit.setText(folder)

    def _browse_target_folder(self) -> None:
        """Browse for target folder."""
        folder = QFileDialog.getExistingDirectory(self, "대상 폴더 선택", "")
        if folder:
            self.target_path_edit.setText(folder)

    def get_source_path(self) -> str:
        """Get the source folder path."""
        return self.source_path_edit.text()

    def get_target_path(self) -> str:
        """Get the target folder path."""
        return self.target_path_edit.text()

    def scan_files(self) -> None:
        """Trigger scan files action."""
        self.scan_requested.emit()

    def organize_files(self) -> None:
        """Trigger organize files action."""
        self.organize_requested.emit()

    def preview_organization(self) -> None:
        """Trigger preview organization action."""
        self.preview_requested.emit()
