"""
Scan Controller Implementation

This module contains the ScanController class that manages file scanning
business logic and coordinates between the UI layer and core scanning services.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from anivault.core.file_grouper import FileGrouper
from anivault.core.models import ScannedFile
from anivault.core.parser.anitopy_parser import AnitopyParser
from anivault.core.parser.models import ParsingResult
from anivault.gui.models import FileItem
from anivault.gui.workers import FileScannerWorker
from anivault.shared.metadata_models import FileMetadata

logger = logging.getLogger(__name__)


class ScanController(QObject):
    """
    Controller for managing file scanning operations.

    This controller handles the business logic for file scanning, including:
    - Directory scanning and file discovery
    - File parsing and metadata extraction
    - File grouping and organization
    - Progress tracking and error handling

    The controller coordinates between the UI layer and core services,
    providing a clean interface for file scanning operations.
    """

    # Signals for UI communication
    scan_started = Signal()
    scan_progress = Signal(int)  # progress percentage
    scan_finished = Signal(list)  # file_items
    scan_error = Signal(str)  # error message
    files_grouped = Signal(dict)  # grouped_files

    def __init__(self, parent: QObject | None = None):
        """Initialize the scan controller.

        Args:
            parent: Parent QObject for Qt parent-child relationship
        """
        super().__init__(parent)

        # Initialize components
        self.file_grouper = FileGrouper()
        self.parser = AnitopyParser()

        # Thread management
        self.scanner_thread: QThread | None = None
        self.scanner_worker: FileScannerWorker | None = None

        # State
        self.is_scanning = False
        self.scanned_files: list[FileItem] = []

        logger.debug("ScanController initialized")

    def scan_directory(self, directory_path: Path) -> None:
        """Start scanning a directory for media files.

        Args:
            directory_path: Path to the directory to scan

        Raises:
            ValueError: If directory_path is invalid or not accessible
        """
        if not directory_path or not directory_path.exists():
            msg = f"Invalid directory path: {directory_path}"
            raise ValueError(msg)

        if not directory_path.is_dir():
            msg = f"Path is not a directory: {directory_path}"
            raise ValueError(msg)

        if self.is_scanning:
            logger.warning("Scan already in progress, ignoring new scan request")
            return

        logger.info("Starting directory scan: %s", directory_path)
        self._start_scanning_thread(directory_path)

    def cancel_scan(self) -> None:
        """Cancel the current scanning operation."""
        if self.scanner_worker and self.is_scanning:
            logger.info("Cancelling file scan")
            self.scanner_worker.cancel_scan()

    def _group_files_by_filename(self, file_items: list[FileItem]) -> dict:
        """Helper method to group files by filename (for unmatched files).

        Args:
            file_items: List of FileItem objects without TMDB matches

        Returns:
            Dictionary mapping group names to lists of FileItem objects
        """
        # Parse filenames and use FileGrouper for intelligent grouping
        scanned_files = []

        for file_item in file_items:
            try:
                parsed_result = self.parser.parse(file_item.file_path.name)
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to parse '%s': %s", file_item.file_path.name, e)
                parsed_result = ParsingResult(
                    title=file_item.file_name,
                    episode=None,
                    season=None,
                    quality=None,
                    source=None,
                    codec=None,
                    audio=None,
                    release_group=None,
                    confidence=0.0,
                    parser_used="gui_fallback",
                    other_info={"error": str(e)},
                )

            scanned_file = ScannedFile(
                file_path=file_item.file_path,
                metadata=parsed_result,
                file_size=0,
                last_modified=0.0,
            )
            scanned_files.append(scanned_file)

        # Use FileGrouper to group by similarity
        grouped_files = self.file_grouper.group_files(scanned_files)

        # Convert back to FileItem-keyed dict
        result = {}
        for group_name, scanned_list in grouped_files.items():
            file_item_list = []
            for scanned in scanned_list:
                # Find corresponding FileItem
                for fi in file_items:
                    if fi.file_path == scanned.file_path:
                        file_item_list.append(fi)
                        break
            result[group_name] = file_item_list

        return result

    def group_files_by_tmdb_title(self, file_items: list[FileItem]) -> dict:
        """Group files by TMDB title after matching.

        Args:
            file_items: List of FileItem objects with TMDB metadata

        Returns:
            Dictionary mapping TMDB titles to lists of files

        Raises:
            ValueError: If file_items is empty or invalid
        """
        if not file_items:
            raise ValueError("Cannot group empty file list")

        try:
            logger.info("Regrouping %d files by TMDB title", len(file_items))

            # Separate matched and unmatched files
            matched_files = []
            unmatched_files = []

            for file_item in file_items:
                # Check if file has TMDB match using FileMetadata
                has_match = False
                if isinstance(file_item.metadata, FileMetadata):
                    # FileMetadata with tmdb_id indicates successful TMDB match
                    if file_item.metadata.tmdb_id is not None:
                        has_match = True
                        matched_files.append(file_item)
                elif isinstance(file_item.metadata, dict):
                    # Legacy dict format (backward compatibility)
                    match_result = file_item.metadata.get("match_result")
                    if match_result:
                        has_match = True
                        matched_files.append(file_item)

                if not has_match:
                    unmatched_files.append(file_item)

            logger.info(
                "TMDB grouping: %d matched, %d unmatched files",
                len(matched_files),
                len(unmatched_files),
            )

            # Group matched files by TMDB title
            grouped_by_tmdb = {}
            for file_item in matched_files:
                tmdb_title = None

                # Extract title from FileMetadata or dict with MatchResult
                if isinstance(file_item.metadata, FileMetadata):
                    tmdb_title = file_item.metadata.title
                elif isinstance(file_item.metadata, dict):
                    # Dict format with match_result (MatchResult dataclass)
                    match_result = file_item.metadata.get("match_result")
                    if match_result:
                        # match_result is MatchResult dataclass
                        tmdb_title = match_result.title

                if tmdb_title:
                    if tmdb_title not in grouped_by_tmdb:
                        grouped_by_tmdb[tmdb_title] = []
                    grouped_by_tmdb[tmdb_title].append(file_item)

            # For unmatched files, use original filename-based grouping
            if unmatched_files:
                logger.info(
                    "Using filename-based grouping for %d unmatched files",
                    len(unmatched_files),
                )
                # Use the standard group_files method for unmatched files
                unmatched_groups = self._group_files_by_filename(unmatched_files)
                # Merge unmatched groups with TMDB groups
                for group_name, files in unmatched_groups.items():
                    if group_name not in grouped_by_tmdb:
                        grouped_by_tmdb[group_name] = files
                    else:
                        grouped_by_tmdb[group_name].extend(files)

            # Convert FileItem back to ScannedFile for compatibility
            final_groups = {}
            for tmdb_title, items in grouped_by_tmdb.items():
                scanned_files = []
                for file_item in items:
                    # Parse filename
                    parsed_result = self.parser.parse(file_item.file_path.name)

                    # Preserve TMDB metadata from FileMetadata
                    if isinstance(file_item.metadata, FileMetadata):
                        # Convert FileMetadata back to match_result dict for compatibility
                        if file_item.metadata.tmdb_id is not None:
                            match_result_dict = {
                                "id": file_item.metadata.tmdb_id,
                                "title": file_item.metadata.title,
                                "media_type": file_item.metadata.media_type,
                                "genres": file_item.metadata.genres,
                                "overview": file_item.metadata.overview,
                                "vote_average": file_item.metadata.vote_average,
                                "poster_path": file_item.metadata.poster_path,
                            }
                            if not parsed_result.other_info:
                                parsed_result.other_info = {}
                            parsed_result.other_info["match_result"] = match_result_dict
                    elif isinstance(file_item.metadata, dict):
                        # Legacy dict format (backward compatibility)
                        match_result = file_item.metadata.get("match_result")
                        if match_result:
                            if not parsed_result.other_info:
                                parsed_result.other_info = {}
                            parsed_result.other_info["match_result"] = match_result

                    scanned_file = ScannedFile(
                        file_path=file_item.file_path,
                        metadata=parsed_result,
                        file_size=0,
                        last_modified=0.0,
                    )
                    scanned_files.append(scanned_file)

                final_groups[tmdb_title] = scanned_files

            logger.info(
                "TMDB regrouping completed: %d groups (from TMDB titles)",
                len(final_groups),
            )

            # Emit signal for UI update
            self.files_grouped.emit(final_groups)

            return final_groups

        except Exception:
            logger.exception("TMDB-based grouping failed")
            raise

    def group_files(self, file_items: list[FileItem]) -> dict:
        """Group scanned files by similarity.

        Args:
            file_items: List of FileItem objects to group

        Returns:
            Dictionary mapping group names to lists of files

        Raises:
            ValueError: If file_items is empty or invalid
        """
        if not file_items:
            raise ValueError("Cannot group empty file list")

        try:
            logger.info("Starting file grouping for %d files", len(file_items))

            # Convert FileItem objects to ScannedFile objects for grouping
            scanned_files = []

            for file_item in file_items:
                # Parse the filename to get proper metadata
                try:
                    parsed_result = self.parser.parse(file_item.file_path.name)
                    logger.debug(
                        "Parsed '%s' -> title: '%s', confidence: %.2f",
                        file_item.file_path.name,
                        parsed_result.title,
                        parsed_result.confidence,
                    )
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "Failed to parse '%s': %s",
                        file_item.file_path.name,
                        e,
                    )
                    # Fallback to basic metadata
                    parsed_result = ParsingResult(
                        title=file_item.file_name,
                        episode=None,
                        season=None,
                        quality=None,
                        source=None,
                        codec=None,
                        audio=None,
                        release_group=None,
                        confidence=0.0,
                        parser_used="gui_fallback",
                        other_info={"error": str(e)},
                    )

                # Preserve TMDB metadata if it exists in the file_item
                # This is critical for UI updates after TMDB matching
                if isinstance(file_item.metadata, FileMetadata):
                    # Convert FileMetadata to match_result dict for compatibility
                    if file_item.metadata.tmdb_id is not None:
                        match_result_dict = {
                            "id": file_item.metadata.tmdb_id,
                            "title": file_item.metadata.title,
                            "media_type": file_item.metadata.media_type,
                            "genres": file_item.metadata.genres,
                            "overview": file_item.metadata.overview,
                            "vote_average": file_item.metadata.vote_average,
                            "poster_path": file_item.metadata.poster_path,
                        }
                        if not parsed_result.other_info:
                            parsed_result.other_info = {}
                        parsed_result.other_info["match_result"] = match_result_dict
                        logger.debug(
                            "Preserved TMDB metadata for: %s - %s",
                            file_item.file_path.name,
                            file_item.metadata.title,
                        )
                elif isinstance(file_item.metadata, dict):
                    # Legacy dict format (backward compatibility)
                    match_result = file_item.metadata.get("match_result")
                    if match_result:
                        # Inject match_result into parsed_result.other_info
                        if not parsed_result.other_info:
                            parsed_result.other_info = {}
                        parsed_result.other_info["match_result"] = match_result

                        # Get title from MatchResult dataclass
                        title = match_result.title if hasattr(match_result, "title") else "Unknown"
                        logger.debug(
                            "Preserved TMDB metadata for: %s - %s",
                            file_item.file_path.name,
                            title,
                        )

                # Create ScannedFile object for grouping
                scanned_file = ScannedFile(
                    file_path=file_item.file_path,
                    metadata=parsed_result,
                    file_size=0,
                    last_modified=0.0,
                )
                scanned_files.append(scanned_file)

            # Group files using FileGrouper
            grouped_files = self.file_grouper.group_files(scanned_files)

            group_count = len(grouped_files)
            total_files = sum(len(files) for files in grouped_files.values())

            logger.info(
                "File grouping completed: %d groups, %d total files",
                group_count,
                total_files,
            )

            # Emit signal for UI update
            self.files_grouped.emit(grouped_files)

            return grouped_files

        except Exception:
            logger.exception("File grouping failed")
            raise

    def _start_scanning_thread(self, directory_path: Path) -> None:
        """Start the file scanning worker thread.

        Args:
            directory_path: Directory to scan
        """
        # Clean up previous thread if exists
        if self.scanner_thread is not None:
            try:
                if self.scanner_thread.isRunning():
                    self.scanner_worker.cancel_scan()
                    self.scanner_thread.wait()
            except RuntimeError:
                # Thread object was already deleted, ignore
                pass
            finally:
                self.scanner_thread = None
                self.scanner_worker = None

        # Create new worker and thread
        self.scanner_worker = FileScannerWorker()
        self.scanner_thread = QThread()

        # Move worker to thread
        self.scanner_worker.moveToThread(self.scanner_thread)

        # Connect signals
        self.scanner_thread.started.connect(
            lambda: self.scanner_worker.scan_directory(str(directory_path)),
        )

        self.scanner_worker.scan_started.connect(self._on_scan_started)
        self.scanner_worker.file_found.connect(self._on_file_found)
        self.scanner_worker.scan_progress.connect(self._on_scan_progress)
        self.scanner_worker.scan_finished.connect(self._on_scan_finished)
        self.scanner_worker.scan_error.connect(self._on_scan_error)

        # Cleanup connections
        self.scanner_worker.scan_finished.connect(self.scanner_thread.quit)
        self.scanner_worker.scan_error.connect(self.scanner_thread.quit)
        self.scanner_thread.finished.connect(self.scanner_thread.deleteLater)
        self.scanner_thread.finished.connect(self.scanner_worker.deleteLater)

        # Start the thread
        self.scanner_thread.start()
        self.is_scanning = True
        logger.info("Started file scanning thread")

    def _on_scan_started(self) -> None:
        """Handle scan started signal."""
        logger.info("File scan started")
        self.scan_started.emit()

    def _on_file_found(self, file_data: dict) -> None:
        """Handle file found signal."""
        logger.debug("File found: %s", file_data["file_path"])

    def _on_scan_progress(self, progress: int) -> None:
        """Handle scan progress signal."""
        self.scan_progress.emit(progress)

    def _on_scan_finished(self, file_items: list[FileItem]) -> None:
        """Handle scan finished signal."""
        self.scanned_files = file_items
        self.is_scanning = False

        logger.info("File scan completed successfully: %d files found", len(file_items))
        self.scan_finished.emit(file_items)

    def _on_scan_error(self, error_msg: str) -> None:
        """Handle scan error signal."""
        self.is_scanning = False
        logger.error("File scan error: %s", error_msg)
        self.scan_error.emit(error_msg)

    @property
    def has_scanned_files(self) -> bool:
        """Check if there are scanned files available.

        Returns:
            True if files have been scanned, False otherwise
        """
        return bool(self.scanned_files)

    @property
    def scanned_files_count(self) -> int:
        """Get the number of scanned files.

        Returns:
            Number of scanned files
        """
        return len(self.scanned_files)
