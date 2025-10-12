"""
Group Card Widget - Displays a file group as a clickable card.

This widget represents a single file group in the grid view, showing
group name, file count, and anime information if available.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QUrl, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QVBoxLayout, QWidget

from anivault.shared.constants.gui_messages import UIConfig

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

        # Network manager for async poster downloads
        self._network_manager = QNetworkAccessManager(self)
        self._pending_replies: dict[str, QNetworkReply] = {}

        self._setup_card()

    def _setup_card(self) -> None:
        """Set up the card layout and styling (TMDB-style horizontal layout)."""
        # Explicitly set NoFrame to remove QFrame's default border
        # QSS themes will control borders (none by default, visible on hover/selected)
        self.setFrameShape(QFrame.NoFrame)
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
            title_text = anime_info.get("title", UIConfig.UNKNOWN_TITLE)
            original_title = anime_info.get("original_title") or anime_info.get(
                "original_name",
            )

            if original_title and original_title != title_text:
                full_title = f"{title_text} ({original_title})"
            else:
                full_title = title_text

            # Truncate title for display (keep full title in tooltip)
            display_title = self._truncate_group_name(
                full_title,
                max_length=UIConfig.GROUP_CARD_TITLE_MAX_LENGTH,
            )

            title_label = QLabel(display_title)
            title_label.setObjectName("groupTitleLabel")
            title_label.setWordWrap(True)
            title_label.setToolTip(full_title)  # Full title on hover
            info_layout.addWidget(title_label)

            # Date section
            release_date = anime_info.get("first_air_date") or anime_info.get(
                "release_date",
            )
            if release_date:
                date_label = QLabel(release_date)
                date_label.setObjectName("groupDateLabel")
                info_layout.addWidget(date_label)

            # Overview/Description section (3-4 lines with ellipsis)
            overview = anime_info.get("overview", UIConfig.NO_OVERVIEW)
            if overview:
                truncated_overview = self._truncate_text(
                    overview,
                    max_length=UIConfig.GROUP_CARD_OVERVIEW_MAX_LENGTH,
                )
                overview_label = QLabel(truncated_overview)
                overview_label.setObjectName("groupOverviewLabel")
                overview_label.setWordWrap(True)
                overview_label.setMinimumHeight(
                    50
                )  # Allow more vertical space for multi-line text
                overview_label.setToolTip(overview)  # Full text on hover
                info_layout.addWidget(overview_label)

            # File count at bottom
            count_label = QLabel(f"{UIConfig.FOLDER_ICON} {len(self.files)} files")
            count_label.setObjectName("groupCountLabel")
            info_layout.addWidget(count_label)

        else:
            # No TMDB data - show file-based info
            display_name = self._truncate_group_name(self.group_name, max_length=40)
            title_label = QLabel(f"📁 {display_name}")
            title_label.setObjectName("groupTitleLabel")
            title_label.setWordWrap(True)
            title_label.setToolTip(f"📁 {self.group_name}")
            info_layout.addWidget(title_label)

            # File hint
            hint_label = QLabel(f"📝 {self._get_file_hint()}")
            hint_label.setObjectName("animeInfoHint")
            hint_label.setToolTip(
                "Parsed from filename - TMDB details will load automatically",
            )
            info_layout.addWidget(hint_label)

            # File count
            count_label = QLabel(f"📂 {len(self.files)} files")
            count_label.setObjectName("groupCountLabel")
            info_layout.addWidget(count_label)

            # Placeholder message
            placeholder_label = QLabel("🔍 Loading TMDB details...")
            placeholder_label.setObjectName("animeInfoPlaceholder")
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

        # Explicitly remove any frame styling (QLabel inherits from QFrame)
        poster_label.setFrameShape(QFrame.NoFrame)
        poster_label.setLineWidth(0)

        # Try to load poster from TMDB data
        anime_info = self._get_anime_info()
        logger.debug(
            "🎨 Creating poster for group '%s': anime_info=%s",
            self.group_name[:30],
            "YES" if anime_info else "NO",
        )

        if anime_info:
            poster_path = anime_info.get("poster_path")
            # Try both 'title' and 'name' fields (TMDB uses different fields for movies vs TV)
            title = anime_info.get("title") or anime_info.get("name") or "?"
            logger.debug(
                "🎨 Poster widget - title: '%s', poster_path: %s",
                title[:30] if title and title != "?" else "None",
                poster_path[:30] if poster_path else "None",
            )

            # Try to load actual poster image from TMDB
            if poster_path:
                # Pass poster_label for async update
                pixmap = self._load_tmdb_poster(poster_path, poster_label)
                if pixmap and not pixmap.isNull():
                    # Successfully loaded cached poster image
                    scaled_pixmap = pixmap.scaled(
                        100,
                        150,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                    poster_label.setPixmap(scaled_pixmap)
                    logger.debug("✅ Loaded cached poster image for: %s", title[:30])
                    return poster_label
                # If pixmap is None, async download started - show placeholder
                # and poster will be updated when download completes

            # Fallback: Show initial if no poster_path or failed to load
            if title and title not in {UIConfig.UNKNOWN_TITLE, "?"}:
                initial = title[0].upper()
                poster_label.setText(f"🎬\n{initial}")
                poster_label.setObjectName("posterInitial")
                logger.debug(
                    "🎨 Set poster to initial '%s' for: %s",
                    initial,
                    title[:30],
                )
            else:
                # Has poster_path but title is Unknown
                initial = "?"
                poster_label.setText(f"🎬\n{initial}")
                poster_label.setObjectName("posterInitial")
        else:
            # No anime info - show folder icon
            poster_label.setText("📁")
            poster_label.setObjectName("posterFolder")

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
                # Convert MatchResult dataclass to dict if needed
                if hasattr(match_result, "to_dict"):
                    match_result_dict = match_result.to_dict()
                    logger.debug(
                        "Found match result: %s",
                        match_result_dict.get("title", UIConfig.UNKNOWN_TITLE),
                    )
                    return match_result_dict
                # Already a dict
                logger.debug(
                    "Found match result: %s",
                    match_result.get("title", UIConfig.UNKNOWN_TITLE),
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
                    # Convert MatchResult dataclass to dict for widget compatibility
                    if hasattr(match_result, "to_dict"):
                        match_result_dict = match_result.to_dict()
                        title = match_result_dict.get("title", UIConfig.UNKNOWN_TITLE)
                        logger.debug(
                            "✓ Found match_result in ParsingResult.other_info: %s",
                            title,
                        )
                        return match_result_dict
                    # Already a dict
                    title = (
                        match_result.get("title")
                        or match_result.get("name")
                        or UIConfig.UNKNOWN_TITLE
                    )
                    logger.debug(
                        "✓ Found match_result in ParsingResult.other_info: %s",
                        title,
                    )
                    if title == UIConfig.UNKNOWN_TITLE:
                        logger.warning(
                            "⚠️ match_result has no title/name! Keys: %s",
                            list(match_result.keys()),
                        )
                    return match_result
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

    def _load_tmdb_poster(
        self,
        poster_path: str,
        poster_label: QLabel,
    ) -> QPixmap | None:
        """
        Load TMDB poster image from cache or download asynchronously from TMDB.

        Args:
            poster_path: TMDB poster path (e.g., "/abc123.jpg")
            poster_label: QLabel to update when download completes

        Returns:
            QPixmap if cached, None if downloading asynchronously
        """
        try:
            # TMDB image configuration
            tmdb_image_base_url = "https://image.tmdb.org/t/p/"
            poster_size = "w185"  # Small poster size for cards

            # Create cache directory
            cache_dir = Path.home() / ".anivault" / "cache" / "posters"
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Sanitize filename
            filename = poster_path.strip("/").replace("/", "_")
            cache_file = cache_dir / filename

            # Check cache first (synchronous - fast)
            if cache_file.exists():
                logger.debug("📦 Loading poster from cache: %s", filename)
                pixmap = QPixmap(str(cache_file))
                if not pixmap.isNull():
                    return pixmap

            # Download from TMDB asynchronously (non-blocking)
            image_url = f"{tmdb_image_base_url}{poster_size}{poster_path}"
            logger.debug("⬇️ Downloading poster asynchronously: %s", image_url)

            # Create network request
            request = QNetworkRequest(QUrl(image_url))
            request.setTransferTimeout(5000)  # 5 second timeout

            # Start async download
            reply = self._network_manager.get(request)

            # Store reply and cache info for completion handler
            self._pending_replies[image_url] = reply

            # Connect to finished signal with lambda to pass context
            reply.finished.connect(
                lambda: self._on_poster_downloaded(reply, poster_label, cache_file),
            )

            # Return None - poster will be loaded asynchronously
            return None

        except Exception:
            logger.exception("❌ Unexpected error initiating poster download")
            return None

    def _on_poster_downloaded(
        self,
        reply: QNetworkReply,
        poster_label: QLabel,
        cache_file: Path,
    ) -> None:
        """
        Handle poster download completion (async callback).

        Args:
            reply: Network reply with downloaded data
            poster_label: QLabel to update with poster image
            cache_file: Path to save cached poster
        """
        try:
            # Remove from pending
            url = reply.url().toString()
            self._pending_replies.pop(url, None)

            # Check for errors
            if reply.error() != QNetworkReply.NetworkError.NoError:
                logger.warning("❌ Poster download failed: %s", reply.errorString())
                reply.deleteLater()
                return

            # Read downloaded data
            image_data = reply.readAll()

            if not image_data or image_data.isEmpty():
                logger.warning("❌ Downloaded poster data is empty")
                reply.deleteLater()
                return

            # Save to cache
            try:
                cache_file.write_bytes(image_data.data())
                logger.debug("💾 Cached poster: %s", cache_file.name)
            except Exception as e:  # noqa: BLE001 - GUI poster cache error fallback
                logger.warning("❌ Failed to cache poster: %s", e)

            # Load into QPixmap
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                # Update poster label with downloaded image
                scaled_pixmap = pixmap.scaled(
                    100,
                    150,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                poster_label.setPixmap(scaled_pixmap)
                logger.debug("✅ Downloaded and displayed poster: %s", cache_file.name)
            else:
                logger.warning("❌ Failed to load QPixmap from downloaded data")

        except Exception:
            logger.exception("❌ Error processing downloaded poster")
        finally:
            reply.deleteLater()

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
