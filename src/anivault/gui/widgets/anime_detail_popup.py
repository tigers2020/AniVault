"""
Anime Detail Popup - Shows detailed anime information on hover.

This widget displays comprehensive anime information including title,
rating, status, genres, and overview in a tooltip-style popup.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

logger = logging.getLogger(__name__)


class AnimeDetailPopup(QFrame):
    """Popup widget showing detailed anime information on hover."""

    def __init__(self, anime_info: dict, parent: QWidget | None = None):
        """
        Initialize the anime detail popup.

        Args:
            anime_info: Dictionary containing anime information
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.anime_info = anime_info
        # Use ToolTip style for natural hover behavior
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)  # noqa: FBT003 - Qt API
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the popup UI."""
        self.setObjectName("animeDetailPopup")
        self.setMinimumWidth(300)
        self.setMaximumWidth(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Title
        title = self.anime_info.get("title") or self.anime_info.get("name") or "Unknown"
        title_label = QLabel(f"<b>{title}</b>")
        title_label.setWordWrap(True)
        title_label.setObjectName("popupTitleLabel")
        layout.addWidget(title_label)

        # Rating with vote count for credibility
        rating = self.anime_info.get("vote_average")
        vote_count = self.anime_info.get("vote_count")
        if rating:
            rating_text = f"⭐ {rating:.1f}/10"
            if vote_count:
                rating_text += f" ({vote_count:,} votes)"
            rating_label = QLabel(rating_text)
            rating_label.setObjectName("popupRatingLabel")
            layout.addWidget(rating_label)

        # Status line: "Ended | 4 seasons 87 episodes | 24min"
        status_line = self._format_status_line()
        if status_line:
            status_label = QLabel(f"📺 {status_line}")
            status_label.setObjectName("popupStatusLabel")
            layout.addWidget(status_label)

        # Date range: first ~ last air date
        first_date = self.anime_info.get("first_air_date")
        last_date = self.anime_info.get("last_air_date")
        if first_date:
            date_text = f"📅 {first_date}"
            if last_date and last_date != first_date:
                date_text += f" ~ {last_date}"
            date_label = QLabel(date_text)
            date_label.setObjectName("popupDateLabel")
            layout.addWidget(date_label)

        # Genres (up to 3, concise)
        genres = self.anime_info.get("genres", [])
        if genres:
            genre_names = [
                g.get("name", "") if isinstance(g, dict) else str(g) for g in genres[:3]
            ]
            genre_text = "🎭 " + " · ".join(genre_names)
            genre_label = QLabel(genre_text)
            genre_label.setObjectName("popupGenreLabel")
            genre_label.setWordWrap(True)
            layout.addWidget(genre_label)

        # Production companies (up to 2)
        company_names = self._format_company_names()
        if company_names:
            company_label = QLabel(f"🏢 {company_names}")
            company_label.setObjectName("popupCompanyLabel")
            company_label.setWordWrap(True)
            layout.addWidget(company_label)

        # Overview (truncate if too long, max 200 chars)
        overview = self.anime_info.get("overview")
        if overview:
            if len(overview) > 200:
                overview = overview[:197] + "..."
            overview_label = QLabel(overview)
            overview_label.setObjectName("popupOverviewLabel")
            overview_label.setWordWrap(True)
            layout.addWidget(overview_label)

        # Popularity score (if available)
        popularity = self.anime_info.get("popularity")
        if popularity:
            popularity_label = QLabel(f"📊 Popularity: {popularity:.1f}")
            popularity_label.setObjectName("popupPopularityLabel")
            layout.addWidget(popularity_label)

    def _format_status_line(self) -> str | None:
        """
        Format status line with show status, season/episode counts, and runtime.

        Returns:
            Formatted status line or None if no information available
        """
        parts = []

        # Show status
        status = self.anime_info.get("status")
        if status:
            # Map technical status to user-friendly text
            status_map = {
                "Ended": "Ended",
                "Returning Series": "Ongoing",
                "Canceled": "Canceled",
                "In Production": "In Production",
            }
            parts.append(status_map.get(status, status))

        # Seasons & Episodes
        num_seasons = self.anime_info.get("number_of_seasons")
        num_episodes = self.anime_info.get("number_of_episodes")
        if num_seasons or num_episodes:
            season_parts = []
            if num_seasons:
                season_parts.append(f"{num_seasons}시즌")
            if num_episodes:
                season_parts.append(f"{num_episodes}화")
            parts.append(" ".join(season_parts))

        # Runtime per episode
        runtime = self.anime_info.get("episode_run_time", [])
        if runtime and len(runtime) > 0:
            parts.append(f"{runtime[0]}분")

        return " | ".join(parts) if parts else None

    def _format_company_names(self) -> str | None:
        """
        Format production company names.

        Returns:
            Formatted company names (max 2) or None if no companies
        """
        companies = self.anime_info.get("production_companies", [])
        if not companies:
            return None

        # Extract company names and remove duplicates while preserving order
        company_names = []
        seen = set()
        for company in companies:
            if isinstance(company, dict):
                name = company.get("name", "")
                if name and name not in seen:
                    company_names.append(name)
                    seen.add(name)
                    if len(company_names) >= 2:  # Limit to 2 companies
                        break

        return " · ".join(company_names) if company_names else None
