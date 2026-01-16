"""
Scan Controller Implementation

This module contains the ScanController class that manages file scanning
business logic and coordinates between the UI layer and core scanning services.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from anivault.core.data_structures.linked_hash_table import LinkedHashTable
from anivault.core.file_grouper import FileGrouper, Group
from anivault.core.models import ScannedFile
from anivault.core.parser.anitopy_parser import AnitopyParser
from anivault.core.parser.models import ParsingAdditionalInfo, ParsingResult
from anivault.gui.models import FileItem
from anivault.gui.workers import FileScannerWorker
from anivault.shared.errors import (
    AniVaultError,
    AniVaultFileError,
    AniVaultParsingError,
    ErrorCode,
    ErrorContextModel,
)
from anivault.shared.metadata_models import FileMetadata, TMDBMatchResult

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
    scan_started: Signal = Signal()  # Emitted when scan starts
    scan_progress: Signal = Signal(int)  # Emits progress percentage
    scan_finished: Signal = Signal(list)  # Emits list[FileItem]
    scan_error: Signal = Signal(str)  # Emits error message
    files_grouped: Signal = Signal(list)  # Emits list[Group] (NO dict!)

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

    def _group_files_by_filename(self, file_items: list[FileItem]) -> LinkedHashTable[str, list[FileItem]]:
        """Helper method to group files by filename (for unmatched files).

        Args:
            file_items: List of FileItem objects without TMDB matches

        Returns:
            LinkedHashTable mapping group names to lists of FileItem objects
        """
        # Parse filenames and use FileGrouper for intelligent grouping
        from anivault.core.parser.helpers import parse_with_fallback

        scanned_files = []

        for file_item in file_items:
            # Use common parsing helper for consistent error handling
            parsed_result = parse_with_fallback(
                self.parser,
                file_item.file_path.name,
                fallback_title=file_item.file_name,
                fallback_parser_name="gui_fallback",
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

        # Convert back to FileItem-keyed LinkedHashTable
        result = LinkedHashTable[str, list[FileItem]]()
        for group in grouped_files:
            file_item_list = []
            for scanned in group.files:
                # Find corresponding FileItem
                for fi in file_items:
                    if fi.file_path == scanned.file_path:
                        file_item_list.append(fi)
                        break
            result.put(group.title, file_item_list)

        return result

    def group_files_by_tmdb_title(self, file_items: list[FileItem]) -> LinkedHashTable[str, list[ScannedFile]]:
        """Group files by TMDB title after matching.

        Args:
            file_items: List of FileItem objects with TMDB metadata

        Returns:
            LinkedHashTable mapping TMDB titles to lists of ScannedFile objects

        Raises:
            ValueError: If file_items is empty or invalid
        """
        if not file_items:
            raise ValueError("Cannot group empty file list")

        try:
            logger.info("Regrouping %d files by TMDB title", len(file_items))

            # Separate matched and unmatched files
            matched_files, unmatched_files = self._separate_matched_unmatched(file_items)

            logger.info(
                "TMDB grouping: %d matched, %d unmatched files",
                len(matched_files),
                len(unmatched_files),
            )

            # Group matched files by TMDB title
            grouped_by_tmdb = self._group_matched_files(matched_files)

            # Merge unmatched files
            if unmatched_files:
                grouped_by_tmdb = self._merge_unmatched_files(grouped_by_tmdb, unmatched_files)

            # Convert FileItem back to ScannedFile for compatibility
            final_groups = self._convert_to_scanned_files(grouped_by_tmdb)

            logger.info(
                "TMDB regrouping completed: %d groups (from TMDB titles)",
                len(final_groups),
            )

            # Convert LinkedHashTable to list[Group] for signal emission (NO dict!)
            group_list = [Group(title=title, files=files) for title, files in final_groups]
            self.files_grouped.emit(group_list)

            return final_groups

        except (KeyError, ValueError, TypeError, AttributeError) as e:
            # Data parsing errors during TMDB grouping
            context = ErrorContextModel(
                operation="tmdb_grouping",
                additional_data={"error_type": "data_parsing"},
            )
            error = AniVaultParsingError(
                ErrorCode.FILE_GROUPING_FAILED,
                f"TMDB-based grouping failed due to data parsing error: {e}",
                context,
                original_error=e,
            )
            logger.exception("TMDB-based grouping failed: %s", error.message)
            raise error from e
        except (OSError, PermissionError) as e:
            # File I/O errors during grouping
            context = ErrorContextModel(
                operation="tmdb_grouping",
                additional_data={"error_type": "file_io"},
            )
            file_error: AniVaultError = AniVaultFileError(
                ErrorCode.FILE_GROUPING_FAILED,
                f"TMDB-based grouping failed due to file I/O error: {e}",
                context,
                original_error=e,
            )
            logger.exception("TMDB-based grouping failed: %s", file_error.message)
            raise file_error from e
        # pylint: disable-next=broad-exception-caught

        # pylint: disable-next=broad-exception-caught

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Unexpected errors during TMDB grouping
            context = ErrorContextModel(
                operation="tmdb_grouping",
                additional_data={"error_type": "unexpected"},
            )
            unexpected_error = AniVaultError(
                ErrorCode.FILE_GROUPING_FAILED,
                f"TMDB-based grouping failed: {e}",
                context,
                original_error=e,
            )
            logger.exception("TMDB-based grouping failed: %s", unexpected_error.message)
            raise unexpected_error from e

    def _separate_matched_unmatched(self, file_items: list[FileItem]) -> tuple[list[FileItem], list[FileItem]]:
        """Separate files into matched and unmatched based on TMDB metadata.

        Args:
            file_items: List of FileItem objects

        Returns:
            Tuple of (matched_files, unmatched_files)
        """
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

            if not has_match:
                unmatched_files.append(file_item)

        return matched_files, unmatched_files

    def _group_matched_files(self, matched_files: list[FileItem]) -> LinkedHashTable[str, list[FileItem]]:
        """Group matched files by TMDB title.

        Args:
            matched_files: List of matched FileItem objects

        Returns:
            LinkedHashTable mapping TMDB titles to lists of FileItem objects
        """
        grouped_by_tmdb = LinkedHashTable[str, list[FileItem]]()

        for file_item in matched_files:
            # Extract title from FileMetadata
            tmdb_title = None
            if isinstance(file_item.metadata, FileMetadata):
                tmdb_title = file_item.metadata.title

            if tmdb_title:
                existing_files = grouped_by_tmdb.get(tmdb_title)
                if existing_files is None:
                    grouped_by_tmdb.put(tmdb_title, [file_item])
                else:
                    existing_files.append(file_item)

        return grouped_by_tmdb

    def _merge_unmatched_files(
        self,
        grouped_by_tmdb: LinkedHashTable[str, list[FileItem]],
        unmatched_files: list[FileItem],
    ) -> LinkedHashTable[str, list[FileItem]]:
        """Merge unmatched files into existing groups using filename-based grouping.

        Args:
            grouped_by_tmdb: Existing TMDB-based groups
            unmatched_files: List of unmatched FileItem objects

        Returns:
            Updated LinkedHashTable with merged groups
        """
        logger.info(
            "Using filename-based grouping for %d unmatched files",
            len(unmatched_files),
        )

        # Use the standard group_files method for unmatched files
        unmatched_groups = self._group_files_by_filename(unmatched_files)

        # Merge unmatched groups with TMDB groups
        for group_name, files in unmatched_groups:
            existing_files = grouped_by_tmdb.get(group_name)
            if existing_files is None:
                grouped_by_tmdb.put(group_name, files)
            else:
                existing_files.extend(files)

        return grouped_by_tmdb

    def _convert_to_scanned_files(self, grouped_by_tmdb: LinkedHashTable[str, list[FileItem]]) -> LinkedHashTable[str, list[ScannedFile]]:
        """Convert FileItem groups to ScannedFile groups.

        Args:
            grouped_by_tmdb: LinkedHashTable mapping titles to FileItem lists

        Returns:
            LinkedHashTable mapping titles to ScannedFile lists
        """
        final_groups = LinkedHashTable[str, list[ScannedFile]]()

        for tmdb_title, items in grouped_by_tmdb:
            scanned_files = []

            for file_item in items:
                # Parse filename
                parsed_result = self.parser.parse(file_item.file_path.name)

                # Preserve TMDB metadata from FileMetadata
                if isinstance(file_item.metadata, FileMetadata):
                    # Convert FileMetadata to TMDBMatchResult dataclass for type safety
                    if file_item.metadata.tmdb_id is not None:
                        match_result = TMDBMatchResult(
                            id=file_item.metadata.tmdb_id,
                            title=file_item.metadata.title,
                            media_type=file_item.metadata.media_type or "tv",
                            year=file_item.metadata.year,
                            genres=file_item.metadata.genres,
                            overview=file_item.metadata.overview,
                            vote_average=file_item.metadata.vote_average,
                            poster_path=file_item.metadata.poster_path,
                        )
                        parsed_result.additional_info.match_result = match_result

                # Create ScannedFile with ParsingResult
                scanned_file = ScannedFile(
                    file_path=file_item.file_path,
                    metadata=parsed_result,
                    file_size=0,
                    last_modified=0.0,
                )
                scanned_files.append(scanned_file)

            final_groups.put(tmdb_title, scanned_files)

        return final_groups

    def group_files(self, file_items: list[FileItem]) -> list[Group]:
        """Group scanned files by similarity.

        Args:
            file_items: List of FileItem objects to group

        Returns:
            List of Group objects (each with title and files)

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
                # pylint: disable-next=broad-exception-caught

                # pylint: disable-next=broad-exception-caught

                except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught
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
                        additional_info=ParsingAdditionalInfo(error=str(e)),
                    )

                # Preserve TMDB metadata if it exists in the file_item
                # This is critical for UI updates after TMDB matching
                if isinstance(file_item.metadata, FileMetadata):
                    # Convert FileMetadata to TMDBMatchResult dataclass for type safety
                    if file_item.metadata.tmdb_id is not None:
                        match_result = TMDBMatchResult(
                            id=file_item.metadata.tmdb_id,
                            title=file_item.metadata.title,
                            media_type=file_item.metadata.media_type or "tv",
                            year=file_item.metadata.year,
                            genres=file_item.metadata.genres,
                            overview=file_item.metadata.overview,
                            vote_average=file_item.metadata.vote_average,
                            poster_path=file_item.metadata.poster_path,
                        )
                        parsed_result.additional_info.match_result = match_result
                        logger.debug(
                            "Preserved TMDB metadata for: %s - %s",
                            file_item.file_path.name,
                            file_item.metadata.title,
                        )
                # Legacy dict format - NO LONGER USED
                # FileMetadata is now the standard format

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
            total_files = sum(len(group.files) for group in grouped_files)

            logger.info(
                "File grouping completed: %d groups, %d total files",
                group_count,
                total_files,
            )

            # Emit list[Group] directly (NO dict!)
            self.files_grouped.emit(grouped_files)

            return grouped_files

        except (KeyError, ValueError, TypeError, AttributeError) as e:
            # Data parsing errors during file grouping
            context = ErrorContextModel(
                operation="file_grouping",
                additional_data={"error_type": "data_parsing"},
            )
            error = AniVaultParsingError(
                ErrorCode.FILE_GROUPING_FAILED,
                f"File grouping failed due to data parsing error: {e}",
                context,
                original_error=e,
            )
            logger.exception("File grouping failed: %s", error.message)
            raise error from e
        except (OSError, PermissionError) as e:
            # File I/O errors during grouping
            context = ErrorContextModel(
                operation="file_grouping",
                additional_data={"error_type": "file_io"},
            )
            file_error: AniVaultError = AniVaultFileError(
                ErrorCode.FILE_GROUPING_FAILED,
                f"File grouping failed due to file I/O error: {e}",
                context,
                original_error=e,
            )
            logger.exception("File grouping failed: %s", file_error.message)
            raise file_error from e
        # pylint: disable-next=broad-exception-caught

        # pylint: disable-next=broad-exception-caught

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Unexpected errors during file grouping
            context = ErrorContextModel(
                operation="file_grouping",
                additional_data={"error_type": "unexpected"},
            )
            unexpected_error = AniVaultError(
                ErrorCode.FILE_GROUPING_FAILED,
                f"File grouping failed: {e}",
                context,
                original_error=e,
            )
            logger.exception("File grouping failed: %s", unexpected_error.message)
            raise unexpected_error from e

    def _start_scanning_thread(self, directory_path: Path) -> None:
        """Start the file scanning worker thread.

        Args:
            directory_path: Directory to scan
        """
        # Clean up previous thread if exists
        if self.scanner_thread is not None:
            try:
                if self.scanner_thread.isRunning():
                    if self.scanner_worker:
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

    def _on_file_found(self, file_item: FileItem) -> None:
        """Handle file found signal.

        Args:
            file_item: FileItem object with file information (NO dict!)
        """
        logger.debug("File found: %s", file_item.file_path)

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
