"""
Organize Preview Dialog

This module provides a dialog for previewing file organization plan
before actual execution, allowing users to review and confirm changes.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

logger = logging.getLogger(__name__)


class OrganizePreviewDialog(QDialog):
    """Dialog for previewing file organization plan."""

    def __init__(self, plan: list[Any], parent=None):
        """Initialize organize preview dialog.

        Args:
            plan: List of FileOperation objects to preview
            parent: Parent widget
        """
        super().__init__(parent)
        self.plan = plan
        self.confirmed = False

        self.setWindowTitle("파일 정리 미리보기")
        self.setMinimumSize(900, 600)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Header with summary
        header_layout = QHBoxLayout()

        title_label = QLabel("📦 파일 정리 계획")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        count_label = QLabel(f"총 {len(self.plan)}개 파일")
        count_label.setStyleSheet("font-size: 14px; color: #666;")
        header_layout.addWidget(count_label)

        layout.addLayout(header_layout)

        # Info message
        info_label = QLabel(
            "다음 파일들이 정리됩니다. 확인 후 '실행' 버튼을 눌러주세요.\n"
            "💡 고해상도 파일은 메인 폴더로, 낮은 해상도는 low_res 폴더로 이동됩니다."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("padding: 10px; background-color: #e7f3ff; border-radius: 5px;")
        layout.addWidget(info_label)

        # Table to display operations
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["파일명", "현재 위치", "→", "이동 위치"])
        self.table.setRowCount(len(self.plan))

        # Populate table
        for idx, operation in enumerate(self.plan):
            # File name (from source path)
            source_path = Path(operation.source_path)
            name_item = QTableWidgetItem(source_path.name)
            self.table.setItem(idx, 0, name_item)

            # Current location
            current_dir = str(source_path.parent)
            current_item = QTableWidgetItem(current_dir)
            current_item.setToolTip(current_dir)
            self.table.setItem(idx, 1, current_item)

            # Arrow
            arrow_item = QTableWidgetItem("→")
            arrow_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(idx, 2, arrow_item)

            # Destination
            dest_path = Path(operation.destination_path)
            dest_item = QTableWidgetItem(str(dest_path))
            dest_item.setToolTip(str(dest_path))

            # Color code based on operation type
            if hasattr(operation, "operation_type"):
                if str(operation.operation_type) == "OperationType.MOVE":
                    dest_item.setBackground(Qt.lightGray)
                elif str(operation.operation_type) == "OperationType.COPY":
                    dest_item.setBackground(Qt.cyan)

            self.table.setItem(idx, 3, dest_item)

        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setColumnWidth(2, 40)  # Arrow column

        layout.addWidget(self.table)

        # Summary info
        summary_layout = QHBoxLayout()

        # Count statistics
        video_count = sum(1 for op in self.plan if self._is_video_file(op.source_path))
        subtitle_count = len(self.plan) - video_count

        stats_label = QLabel(
            f"📊 비디오: {video_count}개 | 자막: {subtitle_count}개"
        )
        stats_label.setStyleSheet("font-size: 12px; color: #555;")
        summary_layout.addWidget(stats_label)

        summary_layout.addStretch()

        layout.addLayout(summary_layout)

        # Dialog buttons
        button_box = QDialogButtonBox()

        # Execute button (custom)
        self.execute_btn = QPushButton("✅ 실행")
        self.execute_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.execute_btn.clicked.connect(self._on_execute)
        button_box.addButton(self.execute_btn, QDialogButtonBox.AcceptRole)

        # Cancel button
        cancel_btn = button_box.addButton(QDialogButtonBox.Cancel)
        cancel_btn.setText("취소")
        cancel_btn.clicked.connect(self.reject)

        layout.addWidget(button_box)

    def _is_video_file(self, file_path: Path) -> bool:
        """Check if file is a video file.

        Args:
            file_path: Path to check

        Returns:
            True if file is video
        """
        video_extensions = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm"}
        return Path(file_path).suffix.lower() in video_extensions

    def _on_execute(self) -> None:
        """Handle execute button click."""
        self.confirmed = True
        self.accept()

    def is_confirmed(self) -> bool:
        """Check if user confirmed the operation.

        Returns:
            True if confirmed
        """
        return self.confirmed

    def get_plan(self) -> list[Any]:
        """Get the organization plan.

        Returns:
            List of FileOperation objects
        """
        return self.plan


