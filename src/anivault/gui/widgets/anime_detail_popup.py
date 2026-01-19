"""
Anime Detail Popup - Shows detailed anime information on hover.

This widget displays comprehensive anime information including title,
rating, status, genres, and overview in a tooltip-style popup.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from anivault.shared.constants.gui_messages import UIConfig
from anivault.shared.models.metadata import FileMetadata

logger = logging.getLogger(__name__)


class AnimeDetailPopup(QFrame):
    """Popup widget showing detailed anime information on hover."""

    def __init__(self, metadata: FileMetadata, parent: QWidget | None = None):
        """
        Initialize the anime detail popup.

        Args:
            metadata: FileMetadata dataclass instance containing anime information
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.metadata = metadata
        # Use ToolTip style for natural hover behavior
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)  # pylint: disable=line-too-long
        self.setAttribute(
            Qt.WA_ShowWithoutActivating,
            True,  # noqa: FBT003 - Qt API
        )
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the popup UI."""
        self.setObjectName("animeDetailPopup")
        self.setMinimumWidth(UIConfig.POPUP_MIN_WIDTH)
        self.setMaximumWidth(UIConfig.POPUP_MAX_WIDTH)
        self.setMinimumHeight(UIConfig.POPUP_MIN_HEIGHT)
        self.setMaximumHeight(UIConfig.POPUP_MAX_HEIGHT)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            UIConfig.POPUP_CONTENT_MARGIN,
            UIConfig.POPUP_CONTENT_MARGIN,
            UIConfig.POPUP_CONTENT_MARGIN,
            UIConfig.POPUP_CONTENT_MARGIN,
        )
        layout.setSpacing(UIConfig.POPUP_CONTENT_SPACING)

        # Title
        title = self.metadata.title or "Unknown"
        title_label = QLabel(f"<b>{title}</b>")
        title_label.setWordWrap(True)
        title_label.setObjectName("popupTitleLabel")
        layout.addWidget(title_label)

        # Rating (vote_count not available in FileMetadata)
        rating = self.metadata.vote_average
        if rating is not None:
            rating_text = f"⭐ {rating:.1f}/10"
            rating_label = QLabel(rating_text)
            rating_label.setObjectName("popupRatingLabel")
            layout.addWidget(rating_label)

        # Status line: "Ended | 4 seasons 87 episodes | 24min"
        # Note: status, number_of_seasons, number_of_episodes, episode_run_time
        # are not available in FileMetadata, so status_line will be None
        status_line = self._format_status_line()
        if status_line:
            status_label = QLabel(f"📺 {status_line}")
            status_label.setObjectName("popupStatusLabel")
            layout.addWidget(status_label)

        # Date range: year from FileMetadata
        if self.metadata.year is not None:
            date_text = f"📅 {self.metadata.year}"
            date_label = QLabel(date_text)
            date_label.setObjectName("popupDateLabel")
            layout.addWidget(date_label)

        # Genres (up to 3, concise)
        genres = self.metadata.genres
        if genres:
            genre_names = [str(g) for g in genres[:3]]
            genre_text = "🎭 " + " · ".join(genre_names)
            genre_label = QLabel(genre_text)
            genre_label.setObjectName("popupGenreLabel")
            genre_label.setWordWrap(True)
            layout.addWidget(genre_label)

        # Production companies (not available in FileMetadata)
        # Skipped - FileMetadata doesn't have production_companies

        # Overview (show full text with word wrap)
        overview = self.metadata.overview
        if overview:
            # Allow longer overview text to show more context
            if len(overview) > UIConfig.POPUP_OVERVIEW_MAX_CHARS:
                overview = overview[: UIConfig.POPUP_OVERVIEW_MAX_CHARS - 3] + "..."
            overview_label = QLabel(overview)
            overview_label.setObjectName("popupOverviewLabel")
            overview_label.setWordWrap(True)
            # Allow label to expand vertically for longer text
            overview_label.setMinimumHeight(UIConfig.POPUP_OVERVIEW_MIN_HEIGHT)
            layout.addWidget(overview_label)

        # Popularity score (not available in FileMetadata)
        # Skipped - FileMetadata doesn't have popularity

    def _format_status_line(self) -> str | None:
        """
        Format status line with season/episode counts from FileMetadata.

        Note: status, number_of_seasons, number_of_episodes, episode_run_time
        are not available in FileMetadata, so we only show season/episode if available.

        Returns:
            Formatted status line or None if no information available
        """
        parts = []

        # Seasons & Episodes from FileMetadata
        if self.metadata.season is not None:
            parts.append(f"S{self.metadata.season}")
        if self.metadata.episode is not None:
            parts.append(f"E{self.metadata.episode}")

        return " | ".join(parts) if parts else None
