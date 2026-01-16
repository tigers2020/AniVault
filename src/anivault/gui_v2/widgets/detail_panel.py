"""Detail Panel Widget for GUI v2."""

from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, QRect, QSize, Property
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class DetailPanel(QWidget):
    """Sliding detail panel widget."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize detail panel widget."""
        super().__init__(parent)
        self._panel_width = 500
        self._setup_ui()
        self._setup_animation()

    def _setup_ui(self) -> None:
        """Set up the detail panel UI."""
        # Main container
        container = QWidget()
        container.setObjectName("detailPanelContainer")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("detailHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(24, 24, 24, 24)

        # Close button
        close_layout = QHBoxLayout()
        close_layout.setContentsMargins(0, 0, 0, 0)
        close_btn = QPushButton("×")
        close_btn.setObjectName("detailClose")
        close_btn.clicked.connect(self.close_panel)
        close_layout.addStretch()
        close_layout.addWidget(close_btn)
        header_layout.addLayout(close_layout)

        # Title and meta
        self.detail_title = QLabel("unknown")
        self.detail_title.setObjectName("detailTitle")
        header_layout.addWidget(self.detail_title)

        self.detail_meta = QLabel("unknown")
        self.detail_meta.setObjectName("detailMeta")
        header_layout.addWidget(self.detail_meta)

        layout.addWidget(header)

        # Content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("detailScrollArea")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(24)

        # Group info section
        info_section = QWidget()
        info_layout = QVBoxLayout(info_section)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(8)

        info_title = QLabel("그룹 정보")
        info_title.setObjectName("detailSectionTitle")
        info_layout.addWidget(info_title)

        self.detail_info = QLabel("unknown")
        info_layout.addWidget(self.detail_info)

        content_layout.addWidget(info_section)

        # File list section
        files_section = QWidget()
        files_layout = QVBoxLayout(files_section)
        files_layout.setContentsMargins(0, 0, 0, 0)
        files_layout.setSpacing(8)

        files_title = QLabel("파일 목록")
        files_title.setObjectName("detailSectionTitle")
        files_layout.addWidget(files_title)

        self.file_list_widget = QWidget()
        self.file_list_layout = QVBoxLayout(self.file_list_widget)
        self.file_list_layout.setContentsMargins(0, 0, 0, 0)
        self.file_list_layout.setSpacing(8)
        files_layout.addWidget(self.file_list_widget)

        content_layout.addWidget(files_section)

        content_layout.addStretch()

        # Action buttons
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)

        match_btn = QPushButton("TMDB 매칭")
        match_btn.setObjectName("btnActionMatch")
        actions_layout.addWidget(match_btn)

        organize_btn = QPushButton("파일 정리")
        organize_btn.setObjectName("btnActionOrganize")
        actions_layout.addWidget(organize_btn)

        content_layout.addLayout(actions_layout)

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

        # Set main container as widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

    def _setup_animation(self) -> None:
        """Set up slide animation."""
        self._x_pos = 0
        self._animation = QPropertyAnimation(self, b"panelPosition")
        self._animation.setDuration(300)

    def close_panel(self) -> None:
        """Close the detail panel."""
        self.hide_panel()

    def show_panel(self) -> None:
        """Show the detail panel with slide animation."""
        if self.parent():
            parent_width = self.parent().width()
            target_x = parent_width - self._panel_width

            self._animation.setStartValue(self._x_pos)
            self._animation.setEndValue(target_x)
            self._animation.start()
            self.show()

    def hide_panel(self) -> None:
        """Hide the detail panel with slide animation."""
        if self.parent():
            parent_width = self.parent().width()
            target_x = parent_width

            self._animation.setStartValue(self._x_pos)
            self._animation.setEndValue(target_x)
            self._animation.start()

    def panelPosition(self) -> int:
        """Get current panel position."""
        return self._x_pos

    def setPanelPosition(self, pos: int) -> None:
        """Set panel position."""
        self._x_pos = pos
        if self.parent():
            parent = self.parent()
            parent_height = parent.height()
            self.setGeometry(self._x_pos, 0, self._panel_width, parent_height)
            self.raise_()

    panelPosition = Property(int, panelPosition, setPanelPosition)

    def set_group_detail(
        self, title: str, meta: str, info: str, files: list[tuple[str, str]]
    ) -> None:
        """Set group detail information.

        Args:
            title: Group title
            meta: Group metadata
            info: Group info text
            files: List of (file_name, file_meta) tuples
        """
        self.detail_title.setText(title)
        self.detail_meta.setText(meta)
        self.detail_info.setText(info)

        # Clear existing file items
        while self.file_list_layout.count():
            child = self.file_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Add file items
        for file_name, file_meta in files:
            file_item = QWidget()
            file_item.setObjectName("fileItem")
            file_layout = QVBoxLayout(file_item)
            file_layout.setContentsMargins(16, 16, 16, 16)
            file_layout.setSpacing(4)

            name_label = QLabel(file_name)
            name_label.setObjectName("fileName")
            file_layout.addWidget(name_label)

            meta_label = QLabel(file_meta)
            meta_label.setObjectName("fileMeta")
            file_layout.addWidget(meta_label)

            self.file_list_layout.addWidget(file_item)
