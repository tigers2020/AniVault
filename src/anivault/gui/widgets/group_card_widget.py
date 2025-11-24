"""
Group Card Widget - Displays a file group as a clickable card.

This widget represents a single file group in the grid view, showing
group name, file count, and anime information if available.
"""

# pylint: disable=no-name-in-module,invalid-name
# PySide6는 C++ 확장 모듈로 타입 스텁이 완전하지 않아 Pylint가 인식하지 못함
# 런타임에는 정상 작동하며, PySide6-stubs가 설치되어 있어도 Pylint는 인식하지 못함
# invalid-name: PySide6 이벤트 핸들러 메서드 이름은 프레임워크 표준을 따라야 함

from __future__ import annotations

# Standard library imports
import logging
from pathlib import Path
from typing import Any

# Third-party imports
from PySide6.QtCore import QEvent, QPoint, Qt, QUrl, Signal
from PySide6.QtGui import QEnterEvent, QMouseEvent, QPixmap
from PySide6.QtNetwork import (
    QNetworkAccessManager,
    QNetworkReply,
    QNetworkRequest,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QVBoxLayout,
    QWidget,
)

from anivault.core.models import ScannedFile
from anivault.core.parser.models import ParsingResult

# First-party imports
from anivault.shared.constants.gui_messages import UIConfig
from anivault.shared.errors import (
    AniVaultError,
    AniVaultFileError,
    AniVaultNetworkError,
    AniVaultParsingError,
    ErrorCode,
    ErrorContext,
)
from anivault.shared.metadata_models import FileMetadata

from .anime_detail_popup import AnimeDetailPopup

logger = logging.getLogger(__name__)

# Removed AnimeInfo type alias - using FileMetadata directly


class GroupCardWidget(QFrame):
    """Card widget for displaying a file group."""

    # Signal emitted when card is clicked with group_name and files
    cardClicked: Signal = Signal(str, list)  # Emits (group_name: str, files: list)

    def __init__(self, group_name: str, files: list[Any], parent: QWidget | None = None):
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
        self._detail_popup: AnimeDetailPopup | None = None

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
        main_layout = self._create_main_layout()
        poster_label = self._create_poster_widget()
        main_layout.addWidget(poster_label)

        # Right: Information layout
        info_layout = self._create_info_layout()
        main_layout.addLayout(info_layout)

        # Enable context menu and cursor
        self._setup_interactions()

    def _create_main_layout(self) -> QHBoxLayout:
        """Create and configure the main horizontal layout.

        Returns:
            Configured QHBoxLayout
        """
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(
            UIConfig.GROUP_CARD_CONTENT_MARGIN,
            UIConfig.GROUP_CARD_CONTENT_MARGIN,
            UIConfig.GROUP_CARD_CONTENT_MARGIN,
            UIConfig.GROUP_CARD_CONTENT_MARGIN,
        )
        main_layout.setSpacing(UIConfig.GROUP_CARD_MAIN_SPACING)
        return main_layout

    def _create_info_layout(self) -> QVBoxLayout:
        """Create and populate the information layout.

        Returns:
            Configured QVBoxLayout with anime info or file-based info
        """
        info_layout = QVBoxLayout()
        info_layout.setSpacing(UIConfig.GROUP_CARD_INFO_SPACING)

        anime_metadata = self._get_anime_metadata()
        if anime_metadata:
            self._populate_info_with_anime_data(info_layout, anime_metadata)
        else:
            self._populate_info_with_file_data(info_layout)

        # Add stretch to push content to top
        info_layout.addStretch()
        return info_layout

    def _populate_info_with_anime_data(self, info_layout: QVBoxLayout, anime_metadata: FileMetadata) -> None:
        """Populate info layout with anime data from TMDB.

        Args:
            info_layout: Layout to populate
            anime_metadata: FileMetadata instance containing anime information
        """
        # Title section
        title_label = self._create_title_label(anime_metadata)
        info_layout.addWidget(title_label)

        # Date section
        date_label = self._create_date_label(anime_metadata)
        if date_label:
            info_layout.addWidget(date_label)

        # Overview section
        overview_label = self._create_overview_label(anime_metadata)
        if overview_label:
            info_layout.addWidget(overview_label)

        # File count
        count_label = QLabel(f"{UIConfig.FOLDER_ICON} {len(self.files)} files")
        count_label.setObjectName("groupCountLabel")
        info_layout.addWidget(count_label)

    def _populate_info_with_file_data(self, info_layout: QVBoxLayout) -> None:
        """Populate info layout with file-based data when no TMDB info available.

        Args:
            info_layout: Layout to populate
        """
        # Group name as title
        display_name = self._truncate_text(self.group_name, max_length=UIConfig.GROUP_CARD_NAME_MAX_LENGTH)
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

    def _create_title_label(self, anime_metadata: FileMetadata) -> QLabel:
        """Create title label from anime metadata.

        Args:
            anime_metadata: FileMetadata instance containing anime information

        Returns:
            Configured QLabel with title
        """
        title_text = anime_metadata.title or UIConfig.UNKNOWN_TITLE

        # FileMetadata doesn't have original_title, use title only
        full_title = title_text

        display_title = self._truncate_text(
            full_title,
            max_length=UIConfig.GROUP_CARD_TITLE_MAX_LENGTH,
        )

        title_label = QLabel(display_title)
        title_label.setObjectName("groupTitleLabel")
        title_label.setWordWrap(True)
        title_label.setToolTip(full_title)
        return title_label

    def _create_date_label(self, anime_metadata: FileMetadata) -> QLabel | None:
        """Create date label from anime metadata.

        Args:
            anime_metadata: FileMetadata instance containing anime information

        Returns:
            Configured QLabel with date or None if no date available
        """
        if anime_metadata.year is not None:
            # Format year as YYYY for display
            date_label = QLabel(str(anime_metadata.year))
            date_label.setObjectName("groupDateLabel")
            return date_label
        return None

    def _create_overview_label(self, anime_metadata: FileMetadata) -> QLabel | None:
        """Create overview label from anime metadata.

        Args:
            anime_metadata: FileMetadata instance containing anime information

        Returns:
            Configured QLabel with overview or None if no overview available
        """
        overview = anime_metadata.overview
        if overview:
            truncated_overview = self._truncate_text(
                overview,
                max_length=UIConfig.GROUP_CARD_OVERVIEW_MAX_LENGTH,
            )
            overview_label = QLabel(truncated_overview)
            overview_label.setObjectName("groupOverviewLabel")
            overview_label.setWordWrap(True)
            overview_label.setToolTip(overview)
            return overview_label
        return None

    def _setup_interactions(self) -> None:
        """Set up context menu and cursor interactions."""
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.setCursor(Qt.PointingHandCursor)

    def _create_poster_widget(self) -> QLabel:
        """
        Create poster image widget.

        Returns:
            QLabel with poster image or placeholder
        """
        poster_label = QLabel()
        poster_label.setObjectName("posterLabel")
        poster_label.setFixedSize(UIConfig.POSTER_WIDTH, UIConfig.POSTER_HEIGHT)  # 2:3 aspect ratio
        poster_label.setAlignment(Qt.AlignCenter)

        # Explicitly remove any frame styling (QLabel inherits from QFrame)
        poster_label.setFrameShape(QFrame.NoFrame)
        poster_label.setLineWidth(0)

        # Try to load poster from TMDB data
        anime_metadata = self._get_anime_metadata()
        logger.debug(
            "🎨 Creating poster for group '%s': anime_metadata=%s",
            self.group_name[: UIConfig.LOG_TRUNCATE_LENGTH],
            "YES" if anime_metadata else "NO",
        )

        if anime_metadata:
            poster_path = anime_metadata.poster_path
            title = anime_metadata.title or "?"

            logger.debug(
                "🎨 Poster widget - title: '%s', poster_path: %s",
                (title[: UIConfig.LOG_TRUNCATE_LENGTH] if title and title != "?" else "None"),
                (poster_path[: UIConfig.LOG_TRUNCATE_LENGTH] if poster_path else "None"),
            )

            # Try to load actual poster image from TMDB
            if poster_path:
                # Pass poster_label for async update
                pixmap = self._load_tmdb_poster(poster_path, poster_label)
                if pixmap and not pixmap.isNull():
                    # Successfully loaded cached poster image
                    scaled_pixmap = pixmap.scaled(
                        UIConfig.POSTER_WIDTH,
                        UIConfig.POSTER_HEIGHT,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                    poster_label.setPixmap(scaled_pixmap)
                    logger.debug(
                        "✅ Loaded cached poster image for: %s",
                        title[: UIConfig.LOG_TRUNCATE_LENGTH],
                    )
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
                    title[: UIConfig.LOG_TRUNCATE_LENGTH],
                )
            else:
                # Has poster_path but title is Unknown
                initial = "?"
                poster_label.setText(f"🎬\n{initial}")
                poster_label.setObjectName("posterInitial")
        else:
            # No anime metadata - show folder icon
            poster_label.setText("📁")
            poster_label.setObjectName("posterFolder")

        return poster_label

    def _get_anime_metadata(self) -> FileMetadata | None:
        """
        Get anime metadata from the first file.

        Supports both FileItem (with FileMetadata) and ScannedFile
        (with ParsingResult containing TMDBMatchResult).

        Returns:
            FileMetadata instance or None if not available
        """
        if not self.files:
            logger.debug("No files in group card")
            return None

        first_file = self.files[0]

        # Get filename safely (duck typing)
        file_name = getattr(first_file, "file_name", None) or getattr(first_file, "file_path", Path("unknown")).name
        logger.debug("Checking anime metadata for file: %s", file_name)

        # Case 1: FileItem with FileMetadata (direct)
        meta = getattr(first_file, "metadata", None)
        if isinstance(meta, FileMetadata):
            logger.debug("Found FileMetadata: %s", meta.title)
            return meta

        # Case 2: ScannedFile with ParsingResult containing TMDBMatchResult
        # Group.files contains ScannedFile objects, not FileItem
        if isinstance(first_file, ScannedFile):
            parsed_result = getattr(first_file, "metadata", None)
            if parsed_result and isinstance(parsed_result, ParsingResult):
                # Check if TMDB match result exists in additional_info

                match_result = parsed_result.additional_info.match_result
                if match_result:
                    # Convert TMDBMatchResult to FileMetadata
                    file_metadata = FileMetadata(
                        title=match_result.title,
                        file_path=first_file.file_path,
                        file_type=(first_file.file_path.suffix.lstrip(".").lower() if first_file.file_path.suffix else "unknown"),
                        year=match_result.year,
                        season=parsed_result.season,
                        episode=parsed_result.episode,
                        genres=match_result.genres,
                        overview=match_result.overview,
                        poster_path=match_result.poster_path,
                        vote_average=match_result.vote_average,
                        tmdb_id=match_result.id,
                        media_type=match_result.media_type,
                    )
                    logger.debug(
                        "Converted TMDBMatchResult to FileMetadata: %s",
                        file_metadata.title,
                    )
                    return file_metadata
                logger.debug("ScannedFile has ParsingResult but no TMDB match result " "(TMDB matching may not have completed yet)")
                # Return None silently - this is expected before TMDB matching
                return None
            # Note: ScannedFile.metadata is typed as ParsingResult, so this branch is
            # theoretically unreachable. However, we keep the isinstance check for
            # runtime safety and to handle potential edge cases.

        # Case 3: first_file itself might be ParsingResult (unlikely but handle it)
        if isinstance(first_file, ParsingResult):
            match_result = first_file.additional_info.match_result
            if match_result:
                # Need file_path from somewhere - try to get it from files list
                file_path = getattr(self.files[0], "file_path", None) if self.files else None
                if file_path:
                    file_metadata = FileMetadata(
                        title=match_result.title,
                        file_path=file_path,
                        file_type=(file_path.suffix.lstrip(".").lower() if file_path.suffix else "unknown"),
                        year=match_result.year,
                        season=first_file.season,
                        episode=first_file.episode,
                        genres=match_result.genres,
                        overview=match_result.overview,
                        poster_path=match_result.poster_path,
                        vote_average=match_result.vote_average,
                        tmdb_id=match_result.id,
                        media_type=match_result.media_type,
                    )
                    logger.debug(
                        "Converted ParsingResult with TMDBMatchResult to FileMetadata: %s",
                        file_metadata.title,
                    )
                    return file_metadata

        # Log warning only if we have metadata but couldn't process it
        if meta:
            logger.debug(
                "File '%s' has metadata type '%s' but no TMDB match result yet. " "This is normal before TMDB matching completes.",
                file_name,
                type(meta).__name__,
            )
        else:
            logger.debug("File has no metadata attribute or metadata is empty")

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
                return self._truncate_text(parsed_title, UIConfig.FILE_HINT_MAX_LENGTH)

        # Fallback to filename stem
        file_path = getattr(first_file, "file_path", None)
        if file_path:
            stem = Path(file_path).stem
            # Remove common video extensions and clean up
            stem = stem.replace(".", " ").replace("_", " ").replace("-", " ")
            stem = " ".join(stem.split())  # Remove extra whitespace
            if stem:
                return self._truncate_text(stem, UIConfig.FILE_HINT_MAX_LENGTH)

        # Final fallback
        return "Unknown title"

    def _truncate_text(self, text: str, max_length: int = UIConfig.DEFAULT_TRUNCATE_LENGTH) -> str:
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

    def enterEvent(self, event: QEnterEvent) -> None:
        """Show detail popup when mouse enters the card."""
        logger.debug("Mouse entered group card: %s", self.group_name)
        anime_metadata = self._get_anime_metadata()
        if anime_metadata:
            logger.debug("Anime metadata found, showing popup")
            self._show_detail_popup(anime_metadata)
        else:
            logger.debug("No anime metadata available for popup")
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        """Hide detail popup when mouse leaves the card."""
        logger.debug("Mouse left group card: %s", self.group_name)
        self._hide_detail_popup()
        super().leaveEvent(event)

    def _show_detail_popup(self, anime_metadata: FileMetadata) -> None:
        """
        Show a popup with detailed anime information.

        Args:
            anime_metadata: FileMetadata instance containing anime information
        """
        if self._detail_popup:
            self._detail_popup.deleteLater()

        self._detail_popup = AnimeDetailPopup(anime_metadata, self)

        # Position popup to the right of the card
        card_pos = self.mapToGlobal(self.rect().topRight())
        self._detail_popup.move(card_pos.x() + UIConfig.POPUP_POSITION_OFFSET, card_pos.y())

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

    def _show_context_menu(self, position: QPoint) -> None:
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
        if self.parent_widget and hasattr(self.parent_widget, "update_group_name_with_parser"):
            self.parent_widget.update_group_name_with_parser(
                self.group_name,
                self.files,
            )

    def _edit_group_name(self) -> None:
        """Edit group name manually."""
        if self.parent_widget and hasattr(self.parent_widget, "edit_group_name"):
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
            poster_size = UIConfig.TMDB_POSTER_SIZE  # Small poster size for cards

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
            request.setTransferTimeout(UIConfig.NETWORK_TIMEOUT_MS)  # Network timeout

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

        except (ConnectionError, TimeoutError) as e:
            context = ErrorContext(
                operation="initiate_poster_download",
                additional_data={"poster_path": poster_path, "image_url": image_url},
            )
            if isinstance(e, TimeoutError):
                network_error = AniVaultNetworkError(
                    ErrorCode.API_TIMEOUT,
                    f"Poster download timeout: {image_url}",
                    context,
                    original_error=e,
                )
            else:
                network_error = AniVaultNetworkError(
                    ErrorCode.NETWORK_ERROR,
                    f"Poster download connection error: {image_url}",
                    context,
                    original_error=e,
                )
            logger.exception("❌ Error initiating poster download: %s", network_error.message)
            return None
        except (ValueError, AttributeError, RuntimeError) as e:
            # Handle unexpected errors during network request setup
            # (e.g., invalid URL format, missing attributes, Qt runtime errors)
            context = ErrorContext(
                operation="initiate_poster_download",
                additional_data={
                    "poster_path": poster_path,
                    "image_url": image_url,
                    "error_type": type(e).__name__,
                },
            )
            unexpected_error = AniVaultError(
                ErrorCode.API_REQUEST_FAILED,
                f"Unexpected error initiating poster download: {image_url}",
                context,
                original_error=e,
            )
            logger.exception(
                "❌ Unexpected error initiating poster download: %s",
                unexpected_error.message,
            )
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
            except (PermissionError, OSError) as e:
                context = ErrorContext(
                    file_path=str(cache_file),
                    operation="cache_poster",
                )
                cache_error = AniVaultFileError(
                    ErrorCode.FILE_WRITE_ERROR,
                    f"Failed to cache poster: {e}",
                    context,
                    original_error=e,
                )
                logger.warning("❌ Failed to cache poster: %s", cache_error.message)
            except (RuntimeError, MemoryError) as e:
                # Handle unexpected errors during cache write (e.g., memory issues)
                context = ErrorContext(
                    file_path=str(cache_file),
                    operation="cache_poster",
                )
                unexpected_error = AniVaultError(
                    ErrorCode.FILE_WRITE_ERROR,
                    f"Unexpected error caching poster: {e}",
                    context,
                    original_error=e,
                )
                logger.warning("❌ Failed to cache poster: %s", unexpected_error.message)

            # Load into QPixmap
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                # Update poster label with downloaded image
                scaled_pixmap = pixmap.scaled(
                    UIConfig.POSTER_WIDTH,
                    UIConfig.POSTER_HEIGHT,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                poster_label.setPixmap(scaled_pixmap)
                logger.debug("✅ Downloaded and displayed poster: %s", cache_file.name)
            else:
                logger.warning("❌ Failed to load QPixmap from downloaded data")

        except (OSError, PermissionError) as e:
            # File I/O errors during poster processing
            context = ErrorContext(
                file_path=str(cache_file),
                operation="process_poster_download",
            )
            io_error = AniVaultFileError(
                ErrorCode.FILE_ACCESS_ERROR,
                f"File I/O error processing poster: {e}",
                context,
                original_error=e,
            )
            logger.exception("❌ Error processing downloaded poster: %s", io_error.message)
        except (ValueError, TypeError) as e:
            # Image parsing/data processing errors
            context = ErrorContext(
                file_path=str(cache_file),
                operation="parse_poster_image",
            )
            parse_error = AniVaultParsingError(
                ErrorCode.PARSING_ERROR,
                f"Failed to parse poster image: {e}",
                context,
                original_error=e,
            )
            logger.exception("❌ Error processing downloaded poster: %s", parse_error.message)
        except (RuntimeError, AttributeError, MemoryError) as e:
            # Unexpected errors - log and continue (GUI should not crash)
            # Handle Qt runtime errors, missing attributes, or memory issues
            context = ErrorContext(
                file_path=str(cache_file),
                operation="process_poster_download",
            )
            unexpected_error = AniVaultError(
                ErrorCode.APPLICATION_ERROR,
                f"Unexpected error processing poster: {e}",
                context,
                original_error=e,
            )
            logger.exception("❌ Error processing downloaded poster: %s", unexpected_error.message)
        finally:
            reply.deleteLater()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse press event - emit cardClicked signal.

        Args:
            event: Mouse event
        """
        if event.button() == Qt.LeftButton:
            logger.debug("Group card clicked: %s", self.group_name)
            self.cardClicked.emit(self.group_name, self.files)
        super().mousePressEvent(event)
