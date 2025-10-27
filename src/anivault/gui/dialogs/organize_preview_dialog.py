"""
Organize Preview Dialog

This module provides a dialog for previewing file organization plan
before actual execution, allowing users to review and confirm changes.
"""

from __future__ import annotations

import logging

# Import for type checking
import re
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class OrganizePreviewDialog(QDialog):
    """Dialog for previewing file organization plan."""

    def __init__(self, plan: list[Any], parent: QWidget | None = None) -> None:
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

        layout.addLayout(self._create_header())
        layout.addWidget(self._create_info_message())
        layout.addWidget(self._create_table())
        layout.addLayout(self._create_summary())
        layout.addWidget(self._create_buttons())

    def _create_header(self) -> QHBoxLayout:
        """Create header with title and file count."""
        header_layout = QHBoxLayout()

        title_label = QLabel("📦 파일 정리 계획")
        title_label.setProperty("class", "dialog-title")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        count_label = QLabel(f"총 {len(self.plan)}개 파일")
        count_label.setProperty("class", "dialog-subtitle")
        header_layout.addWidget(count_label)

        return header_layout

    def _create_info_message(self) -> QLabel:
        """Create info message explaining the organization process."""
        info_label = QLabel(
            "다음 파일들이 정리됩니다. 확인 후 '실행' 버튼을 눌러주세요.\n"
            "💡 해상도 분류: ✨ 고화질(1080p+)은 메인 폴더로, "
            "📦 저화질(720p 이하)은 low_res 폴더로 이동됩니다.\n"
            "❓ 미분류: 파일명에서 해상도를 감지할 수 없는 경우\n"
            "📁 Season 폴더는 파일명에 'S01E01' 형태가 있을 때만 생성됩니다.\n"
            "🗑️ 파일 정리 완료 후 빈 폴더는 자동으로 제거됩니다.",
        )
        info_label.setWordWrap(True)
        info_label.setProperty("class", "info-message")
        return info_label

    def _create_table(self) -> QTableWidget:
        """Create and populate the operations table."""
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["파일명", "해상도", "분류", "현재 위치", "→", "이동 위치"],
        )
        self.table.setRowCount(len(self.plan))

        self._populate_table_rows()
        self._configure_table_columns()

        return self.table

    def _populate_table_rows(self) -> None:
        """Populate table rows with operation data."""
        for idx, operation in enumerate(self.plan):
            self._add_table_row(idx, operation)

    def _add_table_row(self, idx: int, operation: Any) -> None:
        """Add a single row to the table."""
        source_path = Path(operation.source_path)

        # File name
        name_item = QTableWidgetItem(source_path.name)
        self.table.setItem(idx, 0, name_item)

        # Resolution
        resolution = self._get_resolution(operation)
        resolution_text = resolution if resolution else "감지 실패"
        resolution_item = QTableWidgetItem(resolution_text)
        resolution_item.setTextAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]
        self.table.setItem(idx, 1, resolution_item)

        # Classification
        icon, label = self._classify_resolution(resolution)
        classify_item = QTableWidgetItem(f"{icon} {label}")
        classify_item.setTextAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]

        bg_color, text_color = self._get_quality_colors(label)
        classify_item.setBackground(bg_color)
        classify_item.setForeground(text_color)
        self.table.setItem(idx, 2, classify_item)

        # Current location
        current_dir = str(source_path.parent)
        current_item = QTableWidgetItem(current_dir)
        current_item.setToolTip(current_dir)
        self.table.setItem(idx, 3, current_item)

        # Arrow
        arrow_item = QTableWidgetItem("→")
        arrow_item.setTextAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]
        self.table.setItem(idx, 4, arrow_item)

        # Destination
        dest_path = Path(operation.destination_path)
        dest_item = QTableWidgetItem(str(dest_path))
        dest_item.setToolTip(f"이동 위치: {dest_path!s}")

        if hasattr(operation, "operation_type"):
            if str(operation.operation_type) == "OperationType.MOVE":
                dest_item.setBackground(Qt.lightGray)  # type: ignore[attr-defined]
            elif str(operation.operation_type) == "OperationType.COPY":
                dest_item.setBackground(Qt.cyan)  # type: ignore[attr-defined]

        self.table.setItem(idx, 5, dest_item)

    def _configure_table_columns(self) -> None:
        """Configure table column widths and resize modes."""
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # type: ignore[attr-defined]
        header.setSectionResizeMode(1, QHeaderView.Fixed)  # type: ignore[attr-defined]
        header.setSectionResizeMode(2, QHeaderView.Fixed)  # type: ignore[attr-defined]
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # type: ignore[attr-defined]
        header.setSectionResizeMode(4, QHeaderView.Fixed)  # type: ignore[attr-defined]
        header.setSectionResizeMode(5, QHeaderView.Stretch)  # type: ignore[attr-defined]

        self.table.setColumnWidth(0, 250)
        self.table.setColumnWidth(1, 70)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(4, 40)

        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # type: ignore[attr-defined]

    def _create_summary(self) -> QHBoxLayout:
        """Create summary statistics layout."""
        summary_layout = QHBoxLayout()

        video_count = sum(1 for op in self.plan if self._is_video_file(op.source_path))
        subtitle_count = len(self.plan) - video_count

        stats_label = QLabel(
            f"📊 비디오: {video_count}개 | 자막: {subtitle_count}개",
        )
        stats_label.setProperty("class", "stats-label")
        summary_layout.addWidget(stats_label)

        summary_layout.addStretch()

        return summary_layout

    def _create_buttons(self) -> QDialogButtonBox:
        """Create dialog buttons."""
        button_box = QDialogButtonBox()

        self.execute_btn = QPushButton("✅ 실행")
        self.execute_btn.setProperty("class", "primary-button")
        self.execute_btn.clicked.connect(self._on_execute)
        button_box.addButton(
            self.execute_btn,
            QDialogButtonBox.ButtonRole.AcceptRole,
        )

        cancel_btn = button_box.addButton(
            QDialogButtonBox.StandardButton.Cancel,
        )
        cancel_btn.setText("취소")
        cancel_btn.clicked.connect(self.reject)

        return button_box

    def _get_resolution(self, operation: Any) -> str | None:
        """Extract resolution from filename.

        Args:
            operation: FileOperation with source_path

        Returns:
            Resolution string (e.g., "1080p", "720p") or None
        """
        filename = Path(operation.source_path).name

        # Multiple patterns for resolution detection (must match organizer.py patterns)
        patterns = [
            r"\[(\d+p|4K|UHD|SD)\]",  # [1080p], [4K]
            r"\((\d+p|4K|UHD|SD)\)",  # (1080p), (4K)
            r"\b(\d+p|4K|UHD|SD)\b",  # 1080p, 4K (word boundary)
            r"(\d+p|4K|UHD|SD)\.",  # 1080p.mkv, 4K.mp4
            r"(\d+p|4K|UHD|SD)\s",  # 1080p BluRay, 4K HDR
            r"(\d+p|4K|UHD|SD)$",  # 1080p at end of filename
        ]

        for pattern in patterns:
            resolution_match = re.search(pattern, filename, re.IGNORECASE)
            if resolution_match:
                return resolution_match.group(1).upper()

        # Additional pattern: resolution as width x height (e.g., 1920x1080, 640x480)
        dimension_match = re.search(
            r"(\d{3,4})\s*x\s*(\d{3,4})", filename, re.IGNORECASE
        )
        if dimension_match:
            width = int(dimension_match.group(1))
            height = int(dimension_match.group(2))

            # Map dimension to standard resolution
            if width >= 1920 or height >= 1080:
                return "1080P"
            if width >= 1280 or height >= 720:
                return "720P"
            if width >= 854 or height >= 480:
                return "480P"
            return "SD"

        return None

    def _classify_resolution(self, resolution: str | None) -> tuple[str, str]:
        """Classify resolution as high/low quality.

        Args:
            resolution: Resolution string or None

        Returns:
            Tuple of (icon, label)
        """
        if not resolution:
            return ("❓", "미분류")

        from anivault.shared.constants import VideoQuality

        is_high = VideoQuality.is_high_resolution(resolution)

        if is_high:
            return ("✨", "고화질")
        return ("📦", "저화질")

    def _get_quality_colors(self, quality_label: str) -> tuple[QColor, QColor]:
        """Get theme-aware colors for quality classification.

        Args:
            quality_label: Quality label ("고화질", "저화질", "미분류")

        Returns:
            Tuple of (background_color, text_color)
        """
        # Get current application instance
        app = QApplication.instance()
        if not app or not isinstance(app, QApplication):
            # Fallback colors if no application instance
            fallback_colors = {
                "고화질": (QColor(34, 139, 34), QColor(255, 255, 255)),
                "저화질": (QColor(184, 134, 11), QColor(255, 255, 255)),
                "미분류": (QColor(105, 105, 105), QColor(255, 255, 255)),
            }
            return fallback_colors.get(
                quality_label,
                (QColor(105, 105, 105), QColor(255, 255, 255)),
            )

        # Try to get colors from current stylesheet
        try:
            # Parse current stylesheet to extract CSS variables
            stylesheet = app.styleSheet()

            # Extract quality colors from stylesheet
            color_map = {
                "고화질": ("--quality-high-bg", "--quality-high-text"),
                "저화질": ("--quality-low-bg", "--quality-low-text"),
                "미분류": ("--quality-unknown-bg", "--quality-unknown-text"),
            }

            bg_var, text_var = color_map.get(
                quality_label,
                ("--quality-unknown-bg", "--quality-unknown-text"),
            )

            # Default colors (fallback)
            default_colors = {
                "고화질": (QColor(34, 139, 34), QColor(255, 255, 255)),
                "저화질": (QColor(184, 134, 11), QColor(255, 255, 255)),
                "미분류": (QColor(105, 105, 105), QColor(255, 255, 255)),
            }

            bg_color, text_color = default_colors.get(
                quality_label,
                (QColor(105, 105, 105), QColor(255, 255, 255)),
            )

            # Try to parse colors from stylesheet
            # Look for CSS variable definitions
            bg_match = re.search(rf"{bg_var}:\s*([^;]+);", stylesheet)
            text_match = re.search(rf"{text_var}:\s*([^;]+);", stylesheet)

            if bg_match:
                bg_hex = bg_match.group(1).strip()
                try:
                    bg_color = QColor(bg_hex)
                except (ValueError, TypeError):
                    pass

            if text_match:
                text_hex = text_match.group(1).strip()
                try:
                    text_color = QColor(text_hex)
                except (ValueError, TypeError):
                    pass

            return bg_color, text_color

        except Exception as e:  # noqa: BLE001
            logger.debug("Failed to parse theme colors: %s", e)
            # Return fallback colors
            fallback_colors = {
                "고화질": (QColor(34, 139, 34), QColor(255, 255, 255)),
                "저화질": (QColor(184, 134, 11), QColor(255, 255, 255)),
                "미분류": (QColor(105, 105, 105), QColor(255, 255, 255)),
            }
            return fallback_colors.get(
                quality_label,
                (QColor(105, 105, 105), QColor(255, 255, 255)),
            )

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
