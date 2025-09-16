"""Anime details panel for displaying TMDB information."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QGroupBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..themes import DarkTheme


class AnimeDetailsPanel(QGroupBox):
    """Panel displaying detailed anime information from TMDB."""

    def __init__(self, parent=None) -> None:
        """Initialize the anime details panel."""
        super().__init__("애니 디테일", parent)
        self.theme = DarkTheme()
        self._setup_ui()
        self._populate_sample_data()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Create scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(self.theme.get_scroll_area_style())

        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        # Poster section
        self.poster_label = QLabel()
        self.poster_label.setAlignment(Qt.AlignCenter)
        self.poster_label.setStyleSheet(
            f"""
            QLabel {{
                background-color: {self.theme.get_color('bg_secondary')};
                border: 2px solid {self.theme.get_color('border_primary')};
                border-radius: 8px;
                padding: 20px;
                min-height: 200px;
            }}
        """
        )
        self.poster_label.setText("포스터")
        content_layout.addWidget(self.poster_label)

        # Details section
        details_group = QGroupBox("상세 정보")
        details_group.setStyleSheet(self.theme.get_group_box_style())

        details_layout = QVBoxLayout(details_group)
        details_layout.setSpacing(8)

        # Title
        self.title_label = QLabel("My Anime")
        self.title_label.label_type = "title"
        self.title_label.setStyleSheet(self.theme.get_label_style("title"))
        details_layout.addWidget(self.title_label)

        # Info fields
        info_fields = [
            ("장르", "액션"),
            ("설명", "이곳에 설명이 표시됩니다."),
            ("평점", "8.5 / 10"),
            ("에피소드 수", "24"),
            ("방영일", "2020-04-05"),
            ("제작사", "Kyoto Animation"),
        ]

        for field_name, field_value in info_fields:
            field_widget = self._create_info_field(field_name, field_value)
            details_layout.addWidget(field_widget)

        content_layout.addWidget(details_group)
        content_layout.addStretch()

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

    def _create_info_field(self, field_name: str, field_value: str) -> QWidget:
        """Create an information field widget."""
        field_widget = QFrame()
        field_widget.frame_type = "info"
        field_widget.setStyleSheet(self.theme.get_frame_style("info"))

        layout = QVBoxLayout(field_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Field name
        name_label = QLabel(field_name)
        name_label.label_type = "field_name"
        name_label.setStyleSheet(self.theme.get_label_style("field_name"))

        # Field value
        value_label = QLabel(field_value)
        value_label.label_type = "field_value"
        value_label.setStyleSheet(self.theme.get_label_style("field_value"))
        value_label.setWordWrap(True)

        layout.addWidget(name_label)
        layout.addWidget(value_label)

        return field_widget

    def _populate_sample_data(self) -> None:
        """Populate the panel with sample data."""
        # This is already handled in _setup_ui with sample data
        pass

    def update_anime_details(self, anime_data: dict) -> None:
        """Update the anime details with new data."""
        # Update title
        if "title" in anime_data:
            self.title_label.setText(anime_data["title"])

        # Update poster (placeholder for now)
        if "poster_path" in anime_data:
            # In a real implementation, you would load the actual image
            self.poster_label.setText("포스터\n(이미지 로딩 중...)")

        # Update other fields
        # This would be implemented to update the info fields dynamically
        pass

    def clear_details(self) -> None:
        """Clear all anime details."""
        self.title_label.setText("애니메이션을 선택하세요")
        self.poster_label.setText("포스터")

        # Clear all info fields
        # This would be implemented to clear all dynamic fields
