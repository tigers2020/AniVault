"""Groups View for GUI v2."""

from __future__ import annotations


from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QScrollArea, QWidget

from anivault.core.file_grouper import FileGrouper
from anivault.core.models import ScannedFile
from anivault.core.parser.models import ParsingAdditionalInfo, ParsingResult
from anivault.gui_v2.views.base_view import BaseView
from anivault.gui_v2.widgets.group_card import GroupCard
from anivault.shared.models.metadata import FileMetadata


class GroupsView(BaseView):
    """Groups management view showing group cards in a grid."""

    # Signals
    group_clicked = Signal(int)  # Emits group ID when a card is clicked

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize groups view."""
        super().__init__(parent)
        self._groups: list[dict] = []
        self._file_grouper = FileGrouper()
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the groups view UI."""
        from PySide6.QtWidgets import QVBoxLayout

        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setSpacing(0)

        # Scroll area for groups grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("groupsScrollArea")
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        # Grid container
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(24)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area.setWidget(self.grid_container)
        main_layout.addWidget(scroll_area)

    def set_groups(self, groups: list[dict]) -> None:
        """Set groups data and update display.

        Args:
            groups: List of group dictionaries with keys:
                - id: int
                - title: str
                - season: int
                - episodes: int
                - files: int
                - matched: bool
                - confidence: int (0-100)
                - resolution: str
                - language: str
        """
        self._groups = groups
        self._update_display()

    def set_file_metadata(self, files: list[FileMetadata]) -> None:
        """Build groups from FileMetadata and update display."""
        import logging

        logger = logging.getLogger(__name__)
        logger.info("set_file_metadata called with %d files", len(files))
        if not files:
            logger.warning("Empty file list received, clearing groups")
            self.set_groups([])
            return

        # Convert FileMetadata to ScannedFile for FileGrouper
        scanned_files: list[ScannedFile] = []
        for file_metadata in files:
            # Create ParsingResult from FileMetadata
            parsing_result = ParsingResult(
                title=file_metadata.title,
                episode=file_metadata.episode,
                season=file_metadata.season,
                year=file_metadata.year,
                quality=None,  # Will be extracted by FileGrouper if needed
                release_group=None,
                additional_info=ParsingAdditionalInfo(),
            )

            # Create ScannedFile
            scanned_file = ScannedFile(
                file_path=file_metadata.file_path,
                metadata=parsing_result,
                file_size=file_metadata.file_path.stat().st_size if file_metadata.file_path.exists() else 0,
                last_modified=file_metadata.file_path.stat().st_mtime if file_metadata.file_path.exists() else 0.0,
            )
            scanned_files.append(scanned_file)

        # Use FileGrouper to group files intelligently
        file_groups = self._file_grouper.group_files(scanned_files)

        # Re-group FileGrouper results by series name (not by episode)
        # FileGrouper may group by episode, but we want series-level groups
        import re

        series_groups: dict[str, list[FileMetadata]] = {}

        for group in file_groups:
            # Extract metadata from group files
            group_files_metadata: list[FileMetadata] = []
            for scanned_file in group.files:
                # Find corresponding FileMetadata
                for file_metadata in files:
                    if file_metadata.file_path == scanned_file.file_path:
                        group_files_metadata.append(file_metadata)
                        break

            if not group_files_metadata:
                continue

            # Extract series name from group title (remove episode/season info)
            group_title = group.title
            # Remove episode patterns: " - 01", " - 02", " E01", " E02", etc.
            series_name = re.sub(r"\s*-\s*\d+.*$", "", group_title)
            series_name = re.sub(r"\s*E\d+.*$", "", series_name, flags=re.IGNORECASE)
            series_name = re.sub(r"\s*Episode\s*\d+.*$", "", series_name, flags=re.IGNORECASE)
            series_name = series_name.strip()

            # If series name is empty or too short, use group title
            if not series_name or len(series_name) < 2:
                series_name = group_title

            # Group by series name
            if series_name not in series_groups:
                series_groups[series_name] = []
            series_groups[series_name].extend(group_files_metadata)

        # Convert to display format
        groups: list[dict] = []
        for index, (series_name, all_files) in enumerate(series_groups.items(), start=1):
            # Extract unique seasons and episodes
            seasons = {item.season for item in all_files if item.season is not None}
            episodes = {item.episode for item in all_files if item.episode is not None}

            # Check if matched
            matched = any(item.tmdb_id is not None for item in all_files)

            # Extract resolution/quality from file paths or metadata
            resolutions = set()
            for item in all_files:
                file_name_lower = item.file_path.name.lower()
                for res in ["1080p", "720p", "480p", "2160p", "4k", "1440p"]:
                    if res in file_name_lower:
                        resolutions.add(res.upper().replace("P", "p"))
                        break
                # Also check if quality is in ParsingResult metadata
                if hasattr(item, "quality") and item.quality:
                    resolutions.add(item.quality)
            if not resolutions:
                resolutions.add("unknown")

            resolution = next(iter(resolutions), "unknown")

            # Language detection
            language = "unknown"
            for item in all_files:
                file_name_lower = item.file_path.name.lower()
                if any(lang in file_name_lower for lang in ["korean", "kor", "ko"]):
                    language = "ko"
                    break
                if any(lang in file_name_lower for lang in ["japanese", "jap", "ja"]):
                    language = "ja"
                    break
                if any(lang in file_name_lower for lang in ["english", "eng", "en"]):
                    language = "en"
                    break

            groups.append(
                {
                    "id": index,
                    "title": series_name,
                    "season": min(seasons) if seasons else 1,
                    "episodes": len(episodes) if episodes else len(all_files),
                    "files": len(all_files),
                    "matched": matched,
                    "confidence": 100 if matched else 0,
                    "resolution": resolution,
                    "language": language,
                    "file_metadata_list": all_files,  # Store actual FileMetadata list for detail panel
                }
            )

        import logging

        logger = logging.getLogger(__name__)
        logger.info("Created %d groups from %d files", len(groups), len(files))
        self.set_groups(groups)

    def _update_display(self) -> None:
        """Update the groups grid display."""
        import logging

        logger = logging.getLogger(__name__)
        logger.info("_update_display called with %d groups", len(self._groups))
        # Clear existing cards
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Add group cards
        if not self._groups:
            # Show empty state
            logger.warning("No groups to display")
            return

        for i, group in enumerate(self._groups):
            card = GroupCard()
            card.set_group_data(group)
            card.card_clicked.connect(self.group_clicked.emit)

            row = i // 3
            col = i % 3
            self.grid_layout.addWidget(card, row, col)
            # Explicitly show the card and update geometry to ensure proper sizing
            card.show()
            card.updateGeometry()

        # Force layout update and repaint
        self.grid_layout.update()
        # Update the grid container widget to ensure it's visible
        if self.grid_container:
            self.grid_container.update()
            self.grid_container.updateGeometry()
            self.grid_container.show()
            # Force resize to ensure proper layout calculation
            self.grid_container.adjustSize()

    def refresh(self) -> None:
        """Refresh the groups view."""
        self._update_display()
