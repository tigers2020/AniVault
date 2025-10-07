"""
Group Card Widget - Displays a file group as a clickable card.

This widget represents a single file group in the grid view, showing
group name, file count, and anime information if available.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QVBoxLayout, QWidget

logger = logging.getLogger(__name__)


class GroupCardWidget(QFrame):
    """Card widget for displaying a file group."""

    # Signal emitted when card is clicked with group_name and files
    cardClicked = Signal(str, list)  # noqa: N815 (Qt signal naming convention)

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
        """Set up the card layout and styling (TMDB-style horizontal layout)."""
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        # Note: Size is now handled by the central QSS theme system

        # Main horizontal layout (TMDB style: poster on left, info on right)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # Left: Poster image
        poster_label = self._create_poster_widget()
        main_layout.addWidget(poster_label)

        # Right: Information layout
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        # Get anime info first to determine what to display
        anime_info = self._get_anime_info()

        if anime_info:
            # Title section: Korean title + Original title
            title_text = anime_info.get("title", "Unknown")
            original_title = anime_info.get("original_title") or anime_info.get(
                "original_name",
            )

            if original_title and original_title != title_text:
                full_title = f"{title_text} ({original_title})"
            else:
                full_title = title_text

            title_label = QLabel(full_title)
            title_label.setObjectName("groupTitleLabel")
            title_label.setWordWrap(True)
            title_label.setToolTip(full_title)
            title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            info_layout.addWidget(title_label)

            # Date section
            release_date = anime_info.get("first_air_date") or anime_info.get(
                "release_date",
            )
            if release_date:
                date_label = QLabel(release_date)
                date_label.setObjectName("groupDateLabel")
                date_label.setStyleSheet("font-size: 11px; color: #888;")
                info_layout.addWidget(date_label)

            # Overview/Description section (2-3 lines with ellipsis)
            overview = anime_info.get("overview", "")
            if overview:
                truncated_overview = self._truncate_text(overview, max_length=150)
                overview_label = QLabel(truncated_overview)
                overview_label.setObjectName("groupOverviewLabel")
                overview_label.setWordWrap(True)
                overview_label.setStyleSheet("font-size: 12px; color: #555;")
                overview_label.setToolTip(overview)  # Full text on hover
                info_layout.addWidget(overview_label)

            # File count at bottom
            count_label = QLabel(f"📂 {len(self.files)} files")
            count_label.setObjectName("groupCountLabel")
            count_label.setStyleSheet("font-size: 11px; color: #666;")
            info_layout.addWidget(count_label)

        else:
            # No TMDB data - show file-based info
            display_name = self._truncate_group_name(self.group_name, max_length=40)
            title_label = QLabel(f"📁 {display_name}")
            title_label.setObjectName("groupTitleLabel")
            title_label.setWordWrap(True)
            title_label.setToolTip(f"📁 {self.group_name}")
            title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            info_layout.addWidget(title_label)

            # File hint
            hint_label = QLabel(f"📝 {self._get_file_hint()}")
            hint_label.setObjectName("animeInfoHint")
            hint_label.setStyleSheet("font-size: 11px; color: #888;")
            hint_label.setToolTip(
                "Parsed from filename - Click 'Match with TMDB' for details",
            )
            info_layout.addWidget(hint_label)

            # File count
            count_label = QLabel(f"📂 {len(self.files)} files")
            count_label.setObjectName("groupCountLabel")
            count_label.setStyleSheet("font-size: 12px; color: #666;")
            info_layout.addWidget(count_label)

            # Placeholder message
            placeholder_label = QLabel("🔍 Match with TMDB to see details")
            placeholder_label.setObjectName("animeInfoPlaceholder")
            placeholder_label.setStyleSheet(
                "font-size: 11px; color: #999; font-style: italic;",
            )
            info_layout.addWidget(placeholder_label)

        # Add stretch to push content to top
        info_layout.addStretch()

        main_layout.addLayout(info_layout)

        # Enable context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # Set cursor to indicate clickability
        self.setCursor(Qt.PointingHandCursor)

    def _create_poster_widget(self) -> QLabel:
        """
        Create poster image widget.

        Returns:
            QLabel with poster image or placeholder
        """
        poster_label = QLabel()
        poster_label.setObjectName("posterLabel")
        poster_label.setFixedSize(QSize(100, 150))  # 2:3 aspect ratio
        poster_label.setAlignment(Qt.AlignCenter)
        poster_label.setStyleSheet(
            """
            QLabel#posterLabel {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
        """,
        )

        # Try to load poster from TMDB data
        anime_info = self._get_anime_info()
        logger.debug("Creating poster for group '%s': anime_info=%s", 
                    self.group_name[:30], "YES" if anime_info else "NO")
        
        if anime_info:
            poster_path = anime_info.get("poster_path")
            title = anime_info.get("title", "?")
            logger.debug("Poster widget - title: '%s', poster_path: %s", 
                        title[:30] if title else "None", 
                        poster_path[:30] if poster_path else "None")
            
            if poster_path:
                # NOTE: Poster image loading from TMDB will be implemented in future version
                # For now, show placeholder with title initial
                initial = title[0].upper() if title else "?"
                poster_label.setText(f"🎬\n{initial}")
                logger.debug("Set poster to initial: %s", initial)
                poster_label.setStyleSheet(
                    """
                    QLabel#posterLabel {
                        background-color: #007acc;
                        color: white;
                        font-size: 36px;
                        font-weight: bold;
                        border: 1px solid #005a9e;
                        border-radius: 5px;
                    }
                """,
                )
            else:
                # No poster - show file icon
                poster_label.setText("📁")
                poster_label.setStyleSheet(
                    """
                    QLabel#posterLabel {
                        background-color: #e0e0e0;
                        font-size: 48px;
                        border: 1px solid #ccc;
                        border-radius: 5px;
                    }
                """,
                )
        else:
            # No anime info - show folder icon
            poster_label.setText("📁")
            poster_label.setStyleSheet(
                """
                QLabel#posterLabel {
                    background-color: #e0e0e0;
                    font-size: 48px;
                    border: 1px solid #ccc;
                    border-radius: 5px;
                }
            """,
            )

        return poster_label

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
        file_name = (
            getattr(first_file, "file_name", None)
            or getattr(first_file, "file_path", Path("unknown")).name
        )
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
                logger.debug(
                    "Found match result: %s",
                    match_result.get("title", "Unknown"),
                )
                return match_result
            logger.debug("No match_result in metadata dict")

        # Case 2: metadata is ParsingResult or similar object
        # First check if ParsingResult has TMDB data in other_info
        logger.debug("Case 2: metadata type is %s", type(meta).__name__)
        if hasattr(meta, "other_info"):
            logger.debug("metadata has other_info: %s", meta.other_info)
            if isinstance(meta.other_info, dict):
                match_result = meta.other_info.get("match_result")
                if match_result:
                    logger.info("✓ Found match_result in ParsingResult.other_info: %s", 
                               match_result.get("title", "Unknown"))
                    return match_result
                else:
                    logger.debug("other_info is dict but no match_result")
            else:
                logger.debug("other_info is not dict: %s", type(meta.other_info))
        else:
            logger.debug("metadata has no other_info attribute")
        
        # Fallback: Extract basic info from parsed result
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
                logger.debug(
                    "Using parsed metadata as fallback: %s",
                    anime_dict.get("title"),
                )
                return anime_dict
        except Exception as e:  # noqa: BLE001 (defensive catch for metadata parsing)
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
        return text[: max_length - 3] + "..."

    def enterEvent(self, event) -> None:  # noqa: N802 (Qt event method naming)
        """Show detail popup when mouse enters the card."""
        logger.debug("Mouse entered group card: %s", self.group_name)
        anime_info = self._get_anime_info()
        if anime_info:
            logger.debug("Anime info found, showing popup")
            self._show_detail_popup(anime_info)
        else:
            logger.debug("No anime info available for popup")
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 (Qt event method naming)
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

        logger.debug(
            "Showing anime detail popup at (%d, %d)",
            card_pos.x() + 10,
            card_pos.y(),
        )

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
        return group_name[: max_length - 3] + "..."

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
            self.parent_widget.update_group_name_with_parser(
                self.group_name,
                self.files,
            )

    def _edit_group_name(self) -> None:
        """Edit group name manually."""
        if hasattr(self.parent_widget, "edit_group_name"):
            self.parent_widget.edit_group_name(self.group_name, self.files)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt event method naming)
        """
        Handle mouse press event - emit cardClicked signal.

        Args:
            event: Mouse event
        """
        if event.button() == Qt.LeftButton:
            logger.debug("Group card clicked: %s", self.group_name)
            self.cardClicked.emit(self.group_name, self.files)
        super().mousePressEvent(event)
