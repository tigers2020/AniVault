"""
Group Card Widget - Displays a file group as a clickable card.

This widget represents a single file group in the grid view, showing
group name, file count, and anime information if available.
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QMenu, QVBoxLayout, QWidget

logger = logging.getLogger(__name__)


class GroupCardWidget(QFrame):
    """Card widget for displaying a file group."""

    # Signal emitted when card is clicked with group_name and files
    cardClicked = Signal(str, list)

    def __init__(self, group_name: str, files: list, parent: QWidget | None = None):
        """
        Initialize the group card widget.

        Args:
            group_name: Name of the file group
            files: List of files in the group
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.group_name = group_name  # Store full group name
        self.files = files
        self.parent_widget = parent
        self._detail_popup = None

        self._setup_card()

    def _setup_card(self) -> None:
        """Set up the card layout and styling."""
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        # Note: Size is now handled by the central QSS theme system

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # Group title with length limit and tooltip
        display_name = self._truncate_group_name(self.group_name, max_length=25)
        title_label = QLabel(f"📁 {display_name}")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setObjectName("groupTitleLabel")
        title_label.setToolTip(f"📁 {self.group_name}")  # Show full name on hover
        layout.addWidget(title_label)

        # File count
        count_label = QLabel(f"{len(self.files)} files")
        count_label.setAlignment(Qt.AlignCenter)
        count_label.setObjectName("groupCountLabel")
        layout.addWidget(count_label)

        # Anime information placeholder
        anime_info = self._get_anime_info()
        if anime_info:
            # Anime title
            anime_title = anime_info.get("title", "Unknown Anime")
            anime_label = QLabel(f"🎬 {self._truncate_text(anime_title, 30)}")
            anime_label.setAlignment(Qt.AlignCenter)
            anime_label.setObjectName("animeInfoLabel")
            anime_label.setWordWrap(True)
            layout.addWidget(anime_label)

            # Rating (if available)
            rating = anime_info.get("vote_average")
            if rating:
                rating_label = QLabel(f"⭐ {rating:.1f}/10")
                rating_label.setAlignment(Qt.AlignCenter)
                rating_label.setObjectName("animeRatingLabel")
                layout.addWidget(rating_label)

            # Genre (show first genre)
            genres = anime_info.get("genres", [])
            if genres:
                genre_name = genres[0].get("name", "") if isinstance(genres[0], dict) else str(genres[0])
                genre_label = QLabel(f"📂 {genre_name}")
                genre_label.setAlignment(Qt.AlignCenter)
                genre_label.setObjectName("animeGenreLabel")
                layout.addWidget(genre_label)
        else:
            # No anime info available - show helpful placeholder
            placeholder_label = QLabel("🔍 Scan to find anime info")
            placeholder_label.setAlignment(Qt.AlignCenter)
            placeholder_label.setObjectName("animeInfoPlaceholder")
            placeholder_label.setToolTip("Click 'Match with TMDB' to find anime information")
            layout.addWidget(placeholder_label)

            # Add a subtle hint about file parsing
            hint_label = QLabel(f"📝 {self._get_file_hint()}")
            hint_label.setAlignment(Qt.AlignCenter)
            hint_label.setObjectName("animeInfoHint")
            hint_label.setToolTip("Parsed from filename")
            layout.addWidget(hint_label)

        # Enable context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # Set cursor to indicate clickability
        # Note: Styling is now handled by the central QSS theme system
        self.setCursor(Qt.PointingHandCursor)

    def _get_anime_info(self) -> dict | None:
        """
        Get anime information from the first file's metadata.

        Supports both ScannedFile and FileItem with metadata.

        Returns:
            Dictionary with anime information or None if not available
        """
        if not self.files:
            logger.debug("No files in group card")
            return None

        first_file = self.files[0]

        # Get filename safely (duck typing)
        file_name = getattr(first_file, "file_name", None) or getattr(first_file, "file_path", Path("unknown")).name
        logger.debug("Checking anime info for file: %s", file_name)

        # Get metadata attribute (ScannedFile has it, FileItem might have it)
        meta = getattr(first_file, "metadata", None)

        if not meta:
            logger.debug("File has no metadata attribute or metadata is empty")
            return None

        # Case 1: metadata is dict with match_result (TMDB matched)
        if isinstance(meta, dict):
            logger.debug("File has metadata dict with keys: %s", meta.keys())
            match_result = meta.get("match_result")
            if match_result:
                logger.debug("Found match result: %s", match_result.get("title", "Unknown"))
                return match_result
            logger.debug("No match_result in metadata dict")

        # Case 2: metadata is ParsingResult or similar object (not yet matched)
        # Extract basic info from parsed result as fallback
        try:
            anime_dict = {
                "title": getattr(meta, "title", None) or first_file.file_path.stem,
                "genres": getattr(meta, "genres", []),
                "vote_average": getattr(meta, "vote_average", None),
                "first_air_date": getattr(meta, "first_air_date", None),
                "overview": getattr(meta, "overview", None),
                "popularity": getattr(meta, "popularity", None),
            }
            # Only return if we have at least a title
            if anime_dict.get("title"):
                logger.debug("Using parsed metadata as fallback: %s", anime_dict.get("title"))
                return anime_dict
        except Exception as e:
            logger.debug("Failed to extract anime info from metadata: %s", e)

        return None

    def _get_file_hint(self) -> str:
        """
        Get a hint about the parsed file information.

        Returns:
            String hint about the file information
        """
        if not self.files:
            return "No files"

        first_file = self.files[0]

        # Try to get parsed title from metadata
        meta = getattr(first_file, "metadata", None)
        if meta:
            parsed_title = getattr(meta, "title", None)
            if parsed_title and parsed_title.strip():
                return self._truncate_text(parsed_title, 20)

        # Fallback to filename stem
        file_path = getattr(first_file, "file_path", None)
        if file_path:
            stem = Path(file_path).stem
            # Remove common video extensions and clean up
            stem = stem.replace(".", " ").replace("_", " ").replace("-", " ")
            stem = " ".join(stem.split())  # Remove extra whitespace
            if stem:
                return self._truncate_text(stem, 20)

        # Final fallback
        return "Unknown title"

    def _truncate_text(self, text: str, max_length: int = 30) -> str:
        """
        Truncate text to specified length with ellipsis.

        Args:
            text: Text to truncate
            max_length: Maximum length before truncation

        Returns:
            Truncated text with ellipsis if needed
        """
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."

    def enterEvent(self, event) -> None:
        """Show detail popup when mouse enters the card."""
        logger.debug("Mouse entered group card: %s", self.group_name)
        anime_info = self._get_anime_info()
        if anime_info:
            logger.debug("Anime info found, showing popup")
            self._show_detail_popup(anime_info)
        else:
            logger.debug("No anime info available for popup")
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """Hide detail popup when mouse leaves the card."""
        logger.debug("Mouse left group card: %s", self.group_name)
        self._hide_detail_popup()
        super().leaveEvent(event)

    def _show_detail_popup(self, anime_info: dict) -> None:
        """
        Show a popup with detailed anime information.

        Args:
            anime_info: Dictionary containing anime information
        """
        # Import here to avoid circular dependency
        from .anime_detail_popup import AnimeDetailPopup

        if self._detail_popup:
            self._detail_popup.deleteLater()

        self._detail_popup = AnimeDetailPopup(anime_info, self)

        # Position popup to the right of the card
        card_pos = self.mapToGlobal(self.rect().topRight())
        self._detail_popup.move(card_pos.x() + 10, card_pos.y())

        # Ensure popup is on top
        self._detail_popup.raise_()
        self._detail_popup.show()

        logger.debug("Showing anime detail popup at (%d, %d)", card_pos.x() + 10, card_pos.y())

    def _hide_detail_popup(self) -> None:
        """Hide the detail popup."""
        if self._detail_popup:
            self._detail_popup.hide()
            self._detail_popup.deleteLater()
            self._detail_popup = None
            logger.debug("Hiding anime detail popup")

    def _truncate_group_name(self, group_name: str, max_length: int = 25) -> str:
        """
        Truncate group name to specified length with ellipsis.

        Args:
            group_name: Group name to truncate
            max_length: Maximum length before truncation

        Returns:
            Truncated group name with ellipsis if needed
        """
        if len(group_name) <= max_length:
            return group_name

        # Truncate and add ellipsis
        return group_name[:max_length-3] + "..."

    def _show_context_menu(self, position) -> None:
        """
        Show context menu for group card.

        Args:
            position: Position where the context menu should appear
        """
        menu = QMenu(self)

        # Add action to update group name with parser
        update_action = menu.addAction("Update Group Name with Parser")
        update_action.triggered.connect(self._update_group_name_with_parser)

        # Add action to manually edit group name
        edit_action = menu.addAction("Edit Group Name")
        edit_action.triggered.connect(self._edit_group_name)

        # Show menu at cursor position
        menu.exec(self.mapToGlobal(position))

    def _update_group_name_with_parser(self) -> None:
        """Update group name using parser."""
        if hasattr(self.parent_widget, "update_group_name_with_parser"):
            self.parent_widget.update_group_name_with_parser(self.group_name, self.files)

    def _edit_group_name(self) -> None:
        """Edit group name manually."""
        if hasattr(self.parent_widget, "edit_group_name"):
            self.parent_widget.edit_group_name(self.group_name, self.files)

    def mousePressEvent(self, event) -> None:
        """
        Handle mouse press event - emit cardClicked signal.

        Args:
            event: Mouse event
        """
        if event.button() == Qt.LeftButton:
            logger.debug("Group card clicked: %s", self.group_name)
            self.cardClicked.emit(self.group_name, self.files)
        super().mousePressEvent(event)

