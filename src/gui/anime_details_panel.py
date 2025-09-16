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


class AnimeDetailsPanel(QGroupBox):
    """Panel displaying detailed anime information from TMDB."""

    def __init__(self, parent=None) -> None:
        """Initialize the anime details panel."""
        super().__init__("애니 디테일", parent)
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
        scroll_area.setStyleSheet(
            """
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """
        )

        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        # Poster section
        self.poster_label = QLabel()
        self.poster_label.setAlignment(Qt.AlignCenter)
        self.poster_label.setStyleSheet(
            """
            QLabel {
                background-color: #334155;
                border: 2px solid #475569;
                border-radius: 8px;
                padding: 20px;
                min-height: 200px;
            }
        """
        )
        self.poster_label.setText("포스터")
        content_layout.addWidget(self.poster_label)

        # Details section
        details_group = QGroupBox("상세 정보")
        details_group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                border: 2px solid #475569;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
            }
        """
        )

        details_layout = QVBoxLayout(details_group)
        details_layout.setSpacing(8)

        # Title
        self.title_label = QLabel("My Anime")
        self.title_label.setStyleSheet(
            """
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #3b82f6;
                padding: 8px;
                background-color: #334155;
                border-radius: 6px;
            }
        """
        )
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
        field_widget.setStyleSheet(
            """
            QFrame {
                background-color: #334155;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 8px;
            }
        """
        )

        layout = QVBoxLayout(field_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Field name
        name_label = QLabel(field_name)
        name_label.setStyleSheet(
            """
            QLabel {
                font-weight: bold;
                color: #94a3b8;
                font-size: 12px;
            }
        """
        )

        # Field value
        value_label = QLabel(field_value)
        value_label.setStyleSheet(
            """
            QLabel {
                color: #f1f5f9;
                font-size: 14px;
            }
        """
        )
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
