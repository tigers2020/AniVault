"""Anime details panel for displaying TMDB information."""

import logging
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QFrame,
    QGroupBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..themes.theme_manager import get_theme_manager

logger = logging.getLogger(__name__)


class ImageLoaderThread(QThread):
    """Thread for loading images from URLs without blocking the UI."""

    image_loaded = pyqtSignal(QPixmap)
    load_failed = pyqtSignal(str)

    def __init__(self, image_url: str) -> None:
        """Initialize the image loader thread.

        Args:
            image_url (str): URL of the image to load.
        """
        super().__init__()
        self.image_url = image_url

    def run(self) -> None:
        """Load image from URL in background thread."""
        try:
            logger.info(f"Loading image from: {self.image_url}")

            # Download image data
            with urlopen(self.image_url, timeout=10) as response:
                image_data = response.read()

            # Create QPixmap from image data
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                # Scale image to fit poster label (max 300x450)
                scaled_pixmap = pixmap.scaled(300, 450, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_loaded.emit(scaled_pixmap)
                logger.info(f"Successfully loaded image: {self.image_url}")
            else:
                self.load_failed.emit("Failed to load image data")
                logger.error(f"Failed to load image data from: {self.image_url}")

        except URLError as e:
            error_msg = f"Network error loading image: {e!s}"
            self.load_failed.emit(error_msg)
            logger.error(error_msg)
        except Exception as e:
            error_msg = f"Error loading image: {e!s}"
            self.load_failed.emit(error_msg)
            logger.error(error_msg)


class AnimeDetailsPanel(QGroupBox):
    """Panel displaying detailed anime information from TMDB."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the anime details panel."""
        super().__init__("애니 디테일", parent)
        self.theme_manager = get_theme_manager()
        self.image_loader_thread: ImageLoaderThread | None = None
        # Apply theme to the GroupBox first
        self.setStyleSheet(self.theme_manager.current_theme.get_group_box_style())
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
        scroll_area.setStyleSheet(self.theme_manager.current_theme.get_scroll_area_style())

        # Content widget
        content_widget = QWidget()
        content_widget.setStyleSheet(
            f"background-color: {self.theme_manager.get_color('bg_primary')};"
        )
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        # Poster section
        self.poster_label = QLabel()
        self.poster_label.setAlignment(Qt.AlignCenter)
        self.poster_label.setFixedSize(300, 450)  # Fixed size for poster
        self.poster_label.setStyleSheet(
            f"""
            QLabel {{
                background-color: {self.theme_manager.get_color('bg_secondary')};
                border: 2px solid {self.theme_manager.get_color('border_primary')};
                border-radius: 8px;
                padding: 10px;
            }}
        """
        )
        self.poster_label.setText("포스터")
        content_layout.addWidget(self.poster_label)

        # Details section
        details_group = QGroupBox("상세 정보")
        details_group.setStyleSheet(self.theme_manager.current_theme.get_group_box_style())

        details_layout = QVBoxLayout(details_group)
        details_layout.setSpacing(8)

        # Title
        self.title_label = QLabel("My Anime")
        self.title_label.label_type = "title"
        self.title_label.setStyleSheet(self.theme_manager.current_theme.get_label_style("title"))
        details_layout.addWidget(self.title_label)

        # Info fields
        self.info_fields = {}
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
            # Store reference to field widget for later updates
            self.info_fields[field_name] = field_widget

        content_layout.addWidget(details_group)
        content_layout.addStretch()

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

    def _create_info_field(self, field_name: str, field_value: str) -> QWidget:
        """Create an information field widget."""
        field_widget = QFrame()
        field_widget.frame_type = "info"
        field_widget.setStyleSheet(self.theme_manager.current_theme.get_frame_style("info"))

        layout = QVBoxLayout(field_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Field name
        name_label = QLabel(field_name)
        name_label.label_type = "field_name"
        name_label.setStyleSheet(self.theme_manager.current_theme.get_label_style("field_name"))

        # Field value
        value_label = QLabel(field_value)
        value_label.label_type = "field_value"
        value_label.setStyleSheet(self.theme_manager.current_theme.get_label_style("field_value"))
        value_label.setWordWrap(True)

        layout.addWidget(name_label)
        layout.addWidget(value_label)

        return field_widget

    def _populate_sample_data(self) -> None:
        """Populate the panel with sample data."""
        # This is already handled in _setup_ui with sample data
        pass

    def update_anime_details(self, anime_data: dict[str, Any]) -> None:
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

    def display_group_details(self, group: Any) -> None:
        """Display anime details for a selected group.

        Args:
            group: FileGroup object with TMDB information
        """
        if not group:
            self.clear_details()
            return

        # Update title with Korean title if available
        if group.tmdb_info:
            title = group.tmdb_info.korean_title or group.tmdb_info.title
            self.title_label.setText(title)

            # Update other TMDB fields
            self._update_tmdb_fields(group.tmdb_info)
        else:
            # Fallback to group's series title
            title = group.series_title or "제목 없음"
            self.title_label.setText(title)

        # Update poster placeholder
        self.poster_label.setText("포스터\n(로딩 중...)")

        # TODO: Load actual poster image from TMDB if available
        # This would require implementing image loading from URLs

    def _update_tmdb_fields(self, tmdb_info: Any) -> None:
        """Update TMDB information fields.

        Args:
            tmdb_info: TMDBAnime object with metadata
        """
        # Update genres
        if tmdb_info.genres:
            try:
                # Handle both string list and dict list cases
                if isinstance(tmdb_info.genres[0], dict):
                    genres_text = ", ".join([genre.get("name", "") for genre in tmdb_info.genres])
                else:
                    genres_text = ", ".join(tmdb_info.genres)
                self._update_info_field("장르", genres_text)
            except (IndexError, AttributeError, TypeError) as e:
                logger.warning("Error processing genres: %s", str(e))
                self._update_info_field("장르", "정보 없음")
        else:
            self._update_info_field("장르", "정보 없음")

        # Update description
        if tmdb_info.overview:
            self._update_info_field("설명", tmdb_info.overview)
        else:
            self._update_info_field("설명", "설명이 없습니다.")

        # Update rating
        if tmdb_info.vote_average > 0:
            rating_text = f"{tmdb_info.vote_average:.1f} / 10 ({tmdb_info.vote_count}명 평가)"
            self._update_info_field("평점", rating_text)
        else:
            self._update_info_field("평점", "평점 정보 없음")

        # Update episode count
        if tmdb_info.number_of_episodes > 0:
            self._update_info_field("에피소드 수", str(tmdb_info.number_of_episodes))
        else:
            self._update_info_field("에피소드 수", "정보 없음")

        # Update air date
        if tmdb_info.first_air_date:
            air_date_text = tmdb_info.first_air_date.strftime("%Y-%m-%d")
            if tmdb_info.last_air_date and tmdb_info.last_air_date != tmdb_info.first_air_date:
                air_date_text += f" ~ {tmdb_info.last_air_date.strftime('%Y-%m-%d')}"
            self._update_info_field("방영일", air_date_text)
        else:
            self._update_info_field("방영일", "정보 없음")

        # Update networks (production companies)
        if tmdb_info.networks:
            networks_text = ", ".join(tmdb_info.networks)
            self._update_info_field("제작사", networks_text)
        else:
            self._update_info_field("제작사", "정보 없음")

        # Update poster
        if tmdb_info.poster_path:
            self._load_poster_image(tmdb_info.poster_url)
        else:
            self.poster_label.setText("포스터\n(이미지 없음)")

    def _update_info_field(self, field_name: str, field_value: str) -> None:
        """Update a specific info field value.

        Args:
            field_name: Name of the field to update
            field_value: New value for the field
        """
        if field_name in self.info_fields:
            field_widget = self.info_fields[field_name]
            # Find the value label (second child in the layout)
            layout = field_widget.layout()
            if layout and layout.count() >= 2:
                item = layout.itemAt(1)
                if item:
                    value_label = item.widget()
                    if value_label:
                        value_label.setText(field_value)

    def clear_details(self) -> None:
        """Clear all anime details."""
        self.title_label.setText("애니메이션을 선택하세요")
        self.poster_label.setText("포스터")

        # Clear all info fields
        default_values = {
            "장르": "정보 없음",
            "설명": "애니메이션을 선택하세요",
            "평점": "정보 없음",
            "에피소드 수": "정보 없음",
            "방영일": "정보 없음",
            "제작사": "정보 없음",
        }

        for field_name, default_value in default_values.items():
            self._update_info_field(field_name, default_value)

    def _load_poster_image(self, image_url: str) -> None:
        """Load poster image from URL in background thread."""
        # Cancel any existing image loading
        if self.image_loader_thread is not None and self.image_loader_thread.isRunning():
            self.image_loader_thread.quit()
            self.image_loader_thread.wait()

        # Show loading message
        self.poster_label.setText("포스터\n(로딩 중...)")

        # Create and start new image loader thread
        self.image_loader_thread = ImageLoaderThread(image_url)
        # At this point, image_loader_thread is guaranteed to be ImageLoaderThread
        assert self.image_loader_thread is not None
        self.image_loader_thread.image_loaded.connect(self._on_image_loaded)
        self.image_loader_thread.load_failed.connect(self._on_image_load_failed)
        self.image_loader_thread.start()

    def _on_image_loaded(self, pixmap: QPixmap) -> None:
        """Handle successful image loading."""
        self.poster_label.setPixmap(pixmap)
        self.poster_label.setScaledContents(True)
        logger.info("Poster image loaded successfully")

    def _on_image_load_failed(self, error_message: str) -> None:
        """Handle image loading failure."""
        self.poster_label.setText(f"포스터\n(로딩 실패)\n{error_message}")
        logger.error(f"Poster image loading failed: {error_message}")
