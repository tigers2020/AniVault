"""Concrete file processing tasks for AniVault application.

This module provides concrete implementations of WorkerTask classes that
integrate with the actual model components for file processing operations.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import as_completed, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from ..anime_parser import AnimeParser
from ..file_grouper import FileGrouper
from ..file_mover import FileMover
from ..file_scanner import FileScanner, ScanResult
from ..logging_utils import log_operation_error
from ..metadata_cache import MetadataCache
from ..models import AnimeFile, FileGroup, TMDBAnime
from ..thread_executor_manager import get_thread_executor_manager
from ..tmdb_client import TMDBClient, TMDBConfig
from .bulk_update_task import ConcreteBulkUpdateTask
from .file_pipeline_worker import WorkerTask

# Logger for this module
logger = logging.getLogger(__name__)


class ConcreteFileScanningTask(WorkerTask):
    """Concrete task for scanning directories for anime files."""

    def __init__(
        self,
        scan_directories: list[str],
        supported_extensions: list[str],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> None:
        """Initialize the file scanning task.

        Args:
            scan_directories: List of directories to scan
            supported_extensions: List of supported file extensions
            progress_callback: Optional callback for progress updates
        """
        self.scan_directories = scan_directories
        self.supported_extensions = supported_extensions
        self.progress_callback = progress_callback
        self._file_scanner: FileScanner | None = None
        self._result: ScanResult | None = None

    def execute(self) -> list[AnimeFile]:
        """Execute the file scanning.

        Returns:
            List of found anime files
        """
        logger.debug(f"Starting file scanning in {len(self.scan_directories)} directories")

        try:
            # Initialize file scanner
            self._file_scanner = FileScanner()

            # Progress callback is already set in FileScanner constructor

            # Perform scanning
            from pathlib import Path

            self._result = self._file_scanner.scan_directory(Path(self.scan_directories[0]))

            logger.info(f"File scanning completed: {self._result.supported_files} files found")
            return self._result.files

        except Exception as e:
            log_operation_error("file scanning", e, exc_info=True)
            raise

    def get_name(self) -> str:
        """Get task name."""
        return "File Scanning"

    def get_progress_message(self) -> str:
        """Get progress message."""
        return f"Scanning {len(self.scan_directories)} directories for anime files"

    def get_result(self) -> ScanResult | None:
        """Get the scan result."""
        return self._result


class ConcreteFileGroupingTask(WorkerTask):
    """Concrete task for grouping similar anime files."""

    def __init__(
        self,
        files: list[AnimeFile],
        similarity_threshold: float = 0.75,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> None:
        """Initialize the file grouping task.

        Args:
            files: List of files to group
            similarity_threshold: Minimum similarity score for grouping
            progress_callback: Optional callback for progress updates
        """
        self.files = files
        self.similarity_threshold = similarity_threshold
        self.progress_callback = progress_callback
        self._file_grouper: FileGrouper | None = None
        self._groups: list[FileGroup] = []

    def execute(self) -> list[FileGroup]:
        """Execute the file grouping.

        Returns:
            List of file groups
        """
        logger.debug(f"Starting file grouping for {len(self.files)} files")

        try:
            # Initialize file grouper
            self._file_grouper = FileGrouper(similarity_threshold=self.similarity_threshold)

            # Progress callback is already set in FileGrouper constructor

            # Perform grouping
            logger.debug(f"Calling FileGrouper.group_files with {len(self.files)} files")
            result = self._file_grouper.group_files(self.files)
            logger.debug(f"FileGrouper.group_files returned {len(result.groups)} groups")
            self._groups = result.groups

            logger.info(f"File grouping completed: {len(self._groups)} groups created")
            return self._groups

        except Exception as e:
            log_operation_error("file grouping", e, exc_info=True)
            raise

    def get_name(self) -> str:
        """Get task name."""
        return "File Grouping"

    def get_progress_message(self) -> str:
        """Get progress message."""
        return f"Grouping {len(self.files)} files into similar groups"


class ConcreteFileParsingTask(WorkerTask):
    """Concrete task for parsing anime file information."""

    def __init__(self, files: list[AnimeFile], progress_callback: Callable | None = None) -> None:
        """Initialize the file parsing task.

        Args:
            files: List of files to parse
            progress_callback: Optional callback for progress updates
        """
        self.files = files
        self.progress_callback = progress_callback
        self._anime_parser: AnimeParser | None = None
        self._parsed_files: list[AnimeFile] = []

    def execute(self) -> list[AnimeFile]:
        """Execute the file parsing using parallel processing.

        Returns:
            List of parsed files
        """
        logger.debug(f"Starting parallel file parsing for {len(self.files)} files")

        try:
            # Initialize anime parser
            self._anime_parser = AnimeParser()

            # Parse files in parallel using ThreadPoolExecutor
            self._parsed_files = []

            # Use ThreadPoolExecutor for parallel file parsing
            executor_manager = get_thread_executor_manager()
            with executor_manager.get_general_executor() as executor:
                # Submit all parsing tasks
                future_to_file = {
                    executor.submit(self._parse_single_file, file): file
                    for file in self.files
                }

                # Process completed tasks
                for future in as_completed(future_to_file):
                    file = future_to_file[future]

                    try:
                        processed_file = future.result()
                        self._parsed_files.append(processed_file)
                    except Exception as e:
                        logger.warning(f"Failed to parse file {file.filename}: {e}")
                        # Add file with error
                        file.processing_errors.append(f"Parsing failed: {e!s}")
                        self._parsed_files.append(file)

                    # Update progress if callback provided
                    if self.progress_callback:
                        progress = int((len(self._parsed_files) / len(self.files)) * 100)
                        self.progress_callback(progress, len(self.files))

            logger.info(f"Parallel file parsing completed: {len(self._parsed_files)} files parsed")
            return self._parsed_files

        except Exception as e:
            log_operation_error("file parsing", e, exc_info=True)
            raise

    def _parse_single_file(self, file: AnimeFile) -> AnimeFile:
        """Parse a single file (thread-safe worker function).

        Args:
            file: AnimeFile to parse

        Returns:
            AnimeFile with parsed info applied
        """
        try:
            # Validate that we have an AnimeFile object
            if not hasattr(file, "filename"):
                error_msg = f"Invalid object type in parsing task: {type(file)}. Expected AnimeFile."
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Parse the file using the instance parser
            parsed_info = self._anime_parser.parse_filename(file.filename)
            if parsed_info:
                file.parsed_info = parsed_info

            return file

        except Exception as e:
            # Add error to file and return it
            file.processing_errors.append(f"Parsing failed: {e!s}")
            return file

    def get_name(self) -> str:
        """Get task name."""
        return "File Parsing"

    def get_progress_message(self) -> str:
        """Get progress message."""
        return f"Parsing information from {len(self.files)} files"


class ConcreteMetadataRetrievalTask(WorkerTask):
    """Concrete task for retrieving metadata from TMDB."""

    def __init__(
        self, files: list[AnimeFile], api_key: str, progress_callback: Callable | None = None
    ) -> None:
        """Initialize the metadata retrieval task.

        Args:
            files: List of files to get metadata for
            api_key: TMDB API key
            progress_callback: Optional callback for progress updates
        """
        self.files = files
        self.api_key = api_key
        self.progress_callback = progress_callback
        self._tmdb_client: TMDBClient | None = None
        self._files_with_metadata: list[AnimeFile] = []

    def execute(self) -> list[AnimeFile]:
        """Execute the metadata retrieval using parallel processing.

        Returns:
            List of files with metadata
        """
        logger.debug(f"Starting parallel metadata retrieval for {len(self.files)} files")

        try:
            # Initialize TMDB client
            tmdb_config = TMDBConfig(api_key=self.api_key)
            self._tmdb_client = TMDBClient(tmdb_config)

            # Get metadata for each file using parallel processing
            self._files_with_metadata = []
            
            # Use ThreadPoolExecutor for parallel TMDB API calls
            executor_manager = get_thread_executor_manager()
            with executor_manager.get_tmdb_executor() as executor:
                # Submit all metadata retrieval tasks
                future_to_file = {
                    executor.submit(self._retrieve_metadata_for_file, file): file
                    for file in self.files
                }

                # Process completed tasks
                for future in as_completed(future_to_file):
                    file = future_to_file[future]
                    
                    try:
                        processed_file = future.result()
                        self._files_with_metadata.append(processed_file)
                    except Exception as e:
                        logger.warning(f"Failed to get metadata for file {file.filename}: {e}")
                        # Add file with error
                        file.processing_errors.append(f"Metadata retrieval failed: {e!s}")
                        self._files_with_metadata.append(file)

                    # Update progress if callback provided
                    if self.progress_callback:
                        progress = int((len(self._files_with_metadata) / len(self.files)) * 100)
                        self.progress_callback(progress, len(self.files))

            logger.info(
                f"Parallel metadata retrieval completed: {len(self._files_with_metadata)} files processed"
            )
            return self._files_with_metadata

        except Exception as e:
            log_operation_error("metadata retrieval", e, exc_info=True)
            raise

    def _retrieve_metadata_for_file(self, file: AnimeFile) -> AnimeFile:
        """Retrieve metadata for a single file.

        Args:
            file: AnimeFile to retrieve metadata for

        Returns:
            AnimeFile with metadata applied
        """
        try:
            if file.parsed_info and file.parsed_info.title:
                # Search for anime metadata
                search_results = self._tmdb_client.search_tv_series(file.parsed_info.title)

                if search_results:
                    # Use the first (best) result and convert to TMDBAnime
                    tmdb_data = search_results[0]
                    file.tmdb_info = TMDBAnime(
                        tmdb_id=tmdb_data.get("id", 0),
                        title=tmdb_data.get("name", tmdb_data.get("title", "")),
                        original_title=tmdb_data.get(
                            "original_name", tmdb_data.get("original_title", "")
                        ),
                        overview=tmdb_data.get("overview", ""),
                        release_date=tmdb_data.get(
                            "first_air_date", tmdb_data.get("release_date", "")
                        ),
                        poster_path=tmdb_data.get("poster_path", ""),
                        backdrop_path=tmdb_data.get("backdrop_path", ""),
                        vote_average=tmdb_data.get("vote_average", 0.0),
                        vote_count=tmdb_data.get("vote_count", 0),
                        popularity=tmdb_data.get("popularity", 0.0),
                    )

            return file

        except Exception as e:
            # Add error to file and return it
            file.processing_errors.append(f"Metadata retrieval failed: {e!s}")
            return file

    def get_name(self) -> str:
        """Get task name."""
        return "Metadata Retrieval"

    def get_progress_message(self) -> str:
        """Get progress message."""
        return f"Retrieving metadata for {len(self.files)} files"


class ConcreteGroupBasedMetadataRetrievalTask(WorkerTask):
    """Optimized task for retrieving metadata from TMDB on a group basis.

    This task groups files by their parsed title and searches TMDB once per group,
    then applies the metadata to all files in that group.
    """

    def __init__(
        self,
        groups: list[FileGroup],
        api_key: str,
        progress_callback: Callable | None = None,
        db_manager: Any = None,
    ) -> None:
        """Initialize the group-based metadata retrieval task.

        Args:
            groups: List of file groups to get metadata for
            api_key: TMDB API key
            progress_callback: Optional callback for progress updates
            db_manager: Database manager instance for batch operations
        """
        self.groups = groups
        self.api_key = api_key
        self.progress_callback = progress_callback
        self._tmdb_client: TMDBClient | None = None
        self._processed_groups: list[FileGroup] = []
        self._pending_group_selection: dict[str, Any] | None = None
        self._viewmodel: Any | None = None  # Will be set by the ViewModel
        self._should_stop = False  # Flag to indicate if task should stop
        self._db_manager = db_manager  # Database manager for batch operations
        self._collected_metadata: list[TMDBAnime] = []  # Collect metadata for batch saving

    def execute(self) -> list[FileGroup]:
        """Execute the group-based metadata retrieval with batch processing.

        Returns:
            List of groups with metadata applied to their files
        """
        logger.debug(f"Starting group-based metadata retrieval for {len(self.groups)} groups")

        try:
            # Initialize TMDB client
            tmdb_config = TMDBConfig(api_key=self.api_key)
            self._tmdb_client = TMDBClient(tmdb_config)

            # Initialize batch collection
            self._collected_metadata = []
            self._processed_groups = []

            # Process each group
            for i, group in enumerate(self.groups):
                # Check if task should stop
                if self._should_stop:
                    logger.info("Task stop requested, breaking group processing loop")
                    break

                try:
                    # Get representative title from the group
                    representative_title = self._get_representative_title(group)

                    if representative_title:
                        logger.info(f"Searching TMDB for group '{representative_title}'")

                        # Search TMDB once for this group using comprehensive search
                        search_results, needs_selection = self._tmdb_client.search_comprehensive(
                            representative_title, language="ko-KR"
                        )

                        if search_results:
                            if not needs_selection and len(search_results) == 1:
                                # Single result with high confidence, use it directly
                                search_result = search_results[0]
                                tmdb_info = self._tmdb_client._convert_search_result_to_anime(
                                    search_result, "ko-KR"
                                )

                                if tmdb_info is not None:
                                    # Use display title (Korean title if available, otherwise original title)
                                    display_title = tmdb_info.display_title
                                    logger.info(
                                        f"Found TMDB metadata for group '{representative_title}': {display_title}"
                                    )

                                    # Apply metadata to all files in the group
                                    for file in group.files:
                                        file.tmdb_info = tmdb_info

                                    # Update group metadata with display title
                                    group.tmdb_info = tmdb_info
                                    group.series_title = display_title

                                    logger.info(
                                        f"Updated group name to '{display_title}' and applied TMDB metadata to {len(group.files)} files"
                                    )
                            else:
                                # Multiple results or needs selection, request user selection
                                logger.info(
                                    f"Found {len(search_results)} TMDB results for group '{representative_title}', requesting user selection"
                                )

                                # Convert SearchResult objects to dict format for compatibility
                                results_dict = []
                                for search_result in search_results:
                                    result_dict = {
                                        "id": search_result.id,
                                        "name": search_result.title,
                                        "original_name": search_result.original_title,
                                        "first_air_date": search_result.year,
                                        "overview": search_result.overview,
                                        "poster_path": search_result.poster_path,
                                        "vote_average": search_result.vote_average,
                                        "vote_count": search_result.vote_count,
                                        "popularity": search_result.popularity,
                                        "media_type": search_result.media_type,
                                        "quality_score": search_result.quality_score,
                                    }
                                    results_dict.append(result_dict)

                                # Store the group and callback for later use
                                self._pending_group_selection = {
                                    "group": group,
                                    "query": representative_title,
                                    "results": results_dict,
                                }

                                # Request user selection through ViewModel with timeout
                                if hasattr(self, "_viewmodel") and self._viewmodel:
                                    self._viewmodel.tmdb_selection_requested.emit(
                                        representative_title,
                                        results_dict,
                                        self._on_tmdb_selection_callback,
                                    )

                                    # Wait for user selection with timeout
                                    selected_result = self._wait_for_user_selection(
                                        timeout_seconds=30
                                    )

                                    if selected_result:
                                        # User selected a result
                                        tmdb_info = TMDBAnime.from_dict(selected_result)
                                        self._apply_tmdb_metadata_to_group(group, tmdb_info)
                                    else:
                                        # Timeout or no selection - use first result
                                        logger.warning(
                                            f"Using first result for group '{representative_title}' due to timeout or cancellation"
                                        )
                                        tmdb_info = (
                                            self._tmdb_client._convert_search_result_to_anime(
                                                search_results[0], "ko-KR"
                                            )
                                        )
                                        if tmdb_info is not None:
                                            self._apply_tmdb_metadata_to_group(group, tmdb_info)
                                else:
                                    # Fallback: use first result if no ViewModel available
                                    logger.warning(
                                        "No ViewModel available for user selection, using first result"
                                    )
                                    tmdb_info = self._tmdb_client._convert_search_result_to_anime(
                                        search_results[0], "ko-KR"
                                    )
                                    if tmdb_info is not None:
                                        self._apply_tmdb_metadata_to_group(group, tmdb_info)
                        else:
                            logger.warning(
                                f"No TMDB results found for group '{representative_title}'"
                            )
                            # Request manual search with timeout
                            if hasattr(self, "_viewmodel") and self._viewmodel:
                                self._viewmodel.tmdb_selection_requested.emit(
                                    representative_title, [], self._on_tmdb_selection_callback
                                )

                                # Wait for manual search with timeout
                                selected_result = self._wait_for_user_selection(timeout_seconds=30)

                                if selected_result:
                                    # User provided manual search result
                                    tmdb_info = TMDBAnime.from_dict(selected_result)
                                    self._apply_tmdb_metadata_to_group(group, tmdb_info)
                                else:
                                    # Timeout or no manual input - skip this group
                                    logger.warning(
                                        f"Skipping group '{representative_title}' due to no manual input or timeout"
                                    )
                            else:
                                logger.warning("No ViewModel available for manual search")
                    else:
                        logger.warning(f"No representative title found for group {group.group_id}")

                    self._processed_groups.append(group)

                    # Update progress if callback provided
                    if self.progress_callback:
                        progress = int((i + 1) / len(self.groups) * 100)
                        self.progress_callback(progress, len(self.groups))

                except Exception as e:
                    logger.warning(f"Failed to get metadata for group {group.group_id}: {e}")
                    # Add group with error
                    for file in group.files:
                        file.processing_errors.append(f"Group metadata retrieval failed: {e!s}")
                    self._processed_groups.append(group)

            # OPTIMIZED: Batch save all collected metadata to database
            if self._collected_metadata and self._db_manager:
                try:
                    logger.info(
                        f"Batch saving {len(self._collected_metadata)} metadata records to database"
                    )
                    inserted_count, updated_count = self._db_manager.batch_save_anime_metadata(
                        self._collected_metadata
                    )
                    logger.info(
                        f"Batch save completed: {inserted_count} inserted, {updated_count} updated"
                    )
                except Exception as e:
                    logger.error(f"Failed to batch save metadata: {e}")
                    # Continue execution even if batch save fails
            elif self._collected_metadata:
                logger.warning("No database manager provided, skipping batch save")

            logger.info(
                f"Group-based metadata retrieval completed: {len(self._processed_groups)} groups processed"
            )
            return self._processed_groups

        except Exception as e:
            log_operation_error("group-based metadata retrieval", e, exc_info=True)
            raise

    def _get_representative_title(self, group: FileGroup) -> str | None:
        """Get the most representative title from a group for TMDB search.

        Args:
            group: FileGroup to get title from

        Returns:
            Representative title or None if not found
        """
        # Try to get title from best file's parsed info
        if group.best_file and group.best_file.parsed_info and group.best_file.parsed_info.title:
            return group.best_file.parsed_info.title

        # Try to get title from any file's parsed info
        for file in group.files:
            if file.parsed_info and file.parsed_info.title:
                return file.parsed_info.title

        # Fallback to group's series title if available
        if group.series_title:
            return group.series_title

        return None

    def _apply_tmdb_metadata_to_group(self, group: FileGroup, tmdb_info: TMDBAnime) -> None:
        """Apply TMDB metadata to a group and its files with batch processing.

        Args:
            group: FileGroup to apply metadata to
            tmdb_info: TMDBAnime object with metadata
        """
        # Use display title (Korean title if available, otherwise original title)
        display_title = tmdb_info.display_title
        logger.info(f"Applying TMDB metadata to group: {display_title}")

        # Apply metadata to all files in the group
        for file in group.files:
            file.tmdb_info = tmdb_info

        # Update group metadata with display title
        group.tmdb_info = tmdb_info
        group.series_title = display_title

        # Collect metadata for batch saving (OPTIMIZED: No more N+1 queries)
        self._collected_metadata.append(tmdb_info)

        logger.info(
            f"Updated group name to '{display_title}' and applied TMDB metadata to {len(group.files)} files"
        )

    def _wait_for_user_selection(self, timeout_seconds: int = 30) -> dict | None:
        """Wait for user selection with timeout to prevent infinite blocking.

        Args:
            timeout_seconds: Maximum time to wait for user selection

        Returns:
            Selected result dictionary or None if timeout/cancelled
        """
        import time

        start_time = time.time()

        logger.debug(f"Waiting for user selection (timeout: {timeout_seconds}s)")

        while time.time() - start_time < timeout_seconds:
            if self._pending_group_selection is None:
                # User completed selection or cancelled
                logger.debug("User selection completed")
                return None

            # Check if task should stop
            if self._should_stop:
                logger.debug("Task stop requested during user selection wait")
                self._pending_group_selection = None
                return None

            time.sleep(0.1)  # 100ms polling interval

        # Timeout reached
        logger.warning(f"User selection timeout after {timeout_seconds}s, using first result")
        self._pending_group_selection = None
        return None

    def _on_tmdb_selection_callback(self, selected_result: dict) -> None:
        """Callback for when user selects a TMDB result.

        Args:
            selected_result: Selected TMDB result dictionary
        """
        if not self._pending_group_selection:
            logger.warning("No pending group selection found for TMDB callback")
            return

        group = self._pending_group_selection["group"]

        try:
            # Convert selected result to TMDBAnime object
            tmdb_info = TMDBAnime.from_dict(selected_result)
            self._apply_tmdb_metadata_to_group(group, tmdb_info)

            # Clear pending selection
            self._pending_group_selection = None

        except Exception as e:
            log_operation_error("apply selected TMDB result", e)
            # Clear pending selection even on error
            self._pending_group_selection = None

    def set_viewmodel(self, viewmodel: Any) -> None:
        """Set the ViewModel reference for signal communication."""
        self._viewmodel = viewmodel

    def stop(self) -> None:
        """Request the task to stop processing."""
        self._should_stop = True
        # Clear any pending selection to unblock waiting
        if self._pending_group_selection:
            logger.info("Clearing pending group selection due to task stop")
            self._pending_group_selection = None

    def get_name(self) -> str:
        """Get task name."""
        return "Group-based Metadata Retrieval"

    def get_progress_message(self) -> str:
        """Get progress message."""
        return f"Retrieving metadata for {len(self.groups)} groups"


class ConcreteFileMovingTask(WorkerTask):
    """Concrete task for moving and organizing files."""

    def __init__(
        self,
        groups: list[FileGroup],
        target_directory: str,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> None:
        """Initialize the file moving task.

        Args:
            groups: List of file groups to move
            target_directory: Target directory for organized files
            progress_callback: Optional callback for progress updates
        """
        self.groups = groups
        self.target_directory = target_directory
        self.progress_callback = progress_callback
        self._file_mover: FileMover | None = None
        self._moved_files: list[AnimeFile] = []

    def execute(self) -> list[AnimeFile]:
        """Execute the file moving.

        Returns:
            List of moved files
        """
        logger.debug(f"Starting file moving for {len(self.groups)} groups")

        try:
            # Initialize file mover
            self._file_mover = FileMover()

            # Move all groups using TMDB metadata for folder names
            self._moved_files = []
            move_results = self._file_mover.move_file_groups(
                self.groups, Path(self.target_directory)
            )

            # Check if all moves were successful
            all_successful = all(result.success for result in move_results)
            if all_successful:
                # Collect all moved files
                for result in move_results:
                    # Find the corresponding AnimeFile for this result
                    for group in self.groups:
                        for file in group.files:
                            if file.file_path == result.source_path:
                                file.file_path = result.target_path
                                self._moved_files.append(file)
                                break

                # OPTIMIZED: Batch update group processing status
                self._batch_update_group_status(self.groups, is_processed=True)
            else:
                # Add errors to group files
                for result in move_results:
                    if not result.success and result.error_message:
                        for group in self.groups:
                            for file in group.files:
                                if file.file_path == result.source_path:
                                    file.processing_errors.append(result.error_message)
                                    break

                # OPTIMIZED: Batch update group processing status for failed groups
                failed_groups = []
                for group in self.groups:
                    for file in group.files:
                        if file.processing_errors:
                            failed_groups.append(group)
                            break

                if failed_groups:
                    self._batch_update_group_status(failed_groups, is_processed=False)

            # Update progress if callback provided
            if self.progress_callback:
                self.progress_callback(100, len(self.groups))

            # Clean up empty directories after moving files
            logger.info("Cleaning up empty directories...")
            removed_dirs = self._file_mover.cleanup_empty_directories(Path(self.target_directory))
            if removed_dirs:
                logger.info(f"Removed {len(removed_dirs)} empty directories")

            logger.info(f"File moving completed: {len(self._moved_files)} files moved")
            return self._moved_files

        except Exception as e:
            log_operation_error("file moving", e, exc_info=True)
            raise

    def get_name(self) -> str:
        """Get task name."""
        return "File Moving"

    def get_progress_message(self) -> str:
        """Get progress message."""
        return f"Moving {len(self.groups)} file groups to target directory"

    def _batch_update_group_status(self, groups: list[FileGroup], is_processed: bool) -> None:
        """Batch update processing status for file groups.

        This method eliminates N+1 query patterns by collecting all file paths
        and updating their processing status in a single batch operation.

        Args:
            groups: List of file groups to update
            is_processed: New processing status
        """
        try:
            # Collect all file paths from groups
            file_paths = []
            for group in groups:
                for file in group.files:
                    if hasattr(file, "file_path"):
                        file_paths.append(str(file.file_path))

            if file_paths:
                # Create bulk update task for parsed files
                from ..database import db_manager

                bulk_task = ConcreteBulkUpdateTask(
                    update_type="parsed_files",
                    updates=[
                        {"file_path": path, "is_processed": is_processed} for path in file_paths
                    ],
                    db_manager=db_manager,
                )

                updated_count = bulk_task.execute()
                logger.info(f"Batch updated {updated_count} files with is_processed={is_processed}")

                # Update group status in memory
                for group in groups:
                    group.is_processed = is_processed

        except Exception as e:
            logger.error(f"Failed to batch update group status: {e}")
            # Fallback to individual updates
            for group in groups:
                group.is_processed = is_processed


class ConcreteMetadataCachingTask(WorkerTask):
    """Concrete task for caching metadata."""

    def __init__(
        self,
        files: list[AnimeFile],
        cache_duration_hours: int = 24,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> None:
        """Initialize the metadata caching task.

        Args:
            files: List of files to cache metadata for
            cache_duration_hours: How long to cache metadata
            progress_callback: Optional callback for progress updates
        """
        self.files = files
        self.cache_duration_hours = cache_duration_hours
        self.progress_callback = progress_callback
        self._metadata_cache: MetadataCache | None = None
        self._cached_files: list[AnimeFile] = []

    def execute(self) -> list[AnimeFile]:
        """Execute the metadata caching.

        Returns:
            List of files with cached metadata
        """
        logger.debug(f"Starting metadata caching for {len(self.files)} files")

        try:
            # Initialize metadata cache
            self._metadata_cache = MetadataCache()

            # Cache metadata for each file
            self._cached_files = []
            for i, file in enumerate(self.files):
                try:
                    if file.tmdb_info:
                        # Cache the metadata
                        self._metadata_cache.put(str(file.tmdb_info.tmdb_id), file.tmdb_info)

                    self._cached_files.append(file)

                    # Update progress if callback provided
                    if self.progress_callback:
                        progress = int((i + 1) / len(self.files) * 100)
                        self.progress_callback(progress, len(self.files))

                except Exception as e:
                    logger.warning(f"Failed to cache metadata for file {file.filename}: {e}")
                    # Add file with error
                    file.processing_errors.append(f"Caching failed: {e!s}")
                    self._cached_files.append(file)

            logger.info(f"Metadata caching completed: {len(self._cached_files)} files cached")
            return self._cached_files

        except Exception as e:
            log_operation_error("metadata caching", e, exc_info=True)
            raise

    def get_name(self) -> str:
        """Get task name."""
        return "Metadata Caching"

    def get_progress_message(self) -> str:
        """Get progress message."""
        return f"Caching metadata for {len(self.files)} files"
