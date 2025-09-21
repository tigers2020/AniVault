"""Async file processing tasks for AniVault application.

This module provides async implementations of WorkerTask classes that
integrate with the async TMDB client for improved performance and concurrency.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path

from ..async_tmdb_client_pool import async_tmdb_client_context
from ..file_scanner import FileScanner, ScanResult
from ..logging_utils import log_operation_error
from ..models import AnimeFile, FileGroup, TMDBAnime
from .file_pipeline_worker import WorkerTask

# Logger for this module
logger = logging.getLogger(__name__)


class AsyncConcreteMetadataRetrievalTask(WorkerTask):
    """Async task for retrieving metadata from TMDB."""

    def __init__(
        self, files: list[AnimeFile], api_key: str, progress_callback: Callable | None = None
    ) -> None:
        """Initialize the async metadata retrieval task.

        Args:
            files: List of files to get metadata for
            api_key: TMDB API key
            progress_callback: Optional callback for progress updates
        """
        self.files = files
        self.api_key = api_key
        self.progress_callback = progress_callback
        self._files_with_metadata: list[AnimeFile] = []

    async def execute_async(self) -> list[AnimeFile]:
        """Execute the async metadata retrieval using concurrent processing.

        This method orchestrates the concurrent retrieval of TMDB metadata for multiple
        files using asyncio.gather() for optimal performance. The process includes:

        1. Concurrent execution of metadata retrieval tasks for all files
        2. Exception handling for individual file failures without stopping the process
        3. Progress tracking through callback notifications
        4. Comprehensive logging of the operation results

        Files that fail metadata retrieval are still included in the results with
        error information stored in their processing_errors attribute.

        Returns:
            List of files with metadata applied. All input files are included,
            regardless of whether metadata retrieval succeeded or failed.

        Raises:
            Exception: Re-raises any unexpected errors that occur during the
                overall operation setup or execution.
        """

    async def _retrieve_metadata_for_file_async(self, file: AnimeFile) -> AnimeFile:
        """Retrieve metadata for a single file using async TMDB client.

        This method performs the following operations:
        1. Validates that the file has parsed information and a title
        2. Searches TMDB for TV series matching the parsed title
        3. Extracts metadata from the first (best) search result
        4. Creates a TMDBAnime object with comprehensive metadata fields
        5. Handles errors gracefully by logging warnings and adding to processing errors

        The method uses the first search result as the best match, which is typically
        the most relevant result returned by TMDB's search algorithm.

        Args:
            file: AnimeFile to retrieve metadata for. Must have parsed_info.title
                for the search to be performed.

        Returns:
            AnimeFile with metadata applied. The original file is modified in-place
            with the tmdb_info attribute populated if metadata is found.

        Note:
            If no parsed title is available or TMDB search fails, the file is
            returned unchanged with error information added to processing_errors.
        """

    def execute(self) -> list[AnimeFile]:
        """Execute the task synchronously by running the async method.

        Returns:
            List of files with metadata
        """
        return asyncio.run(self.execute_async())

    def get_name(self) -> str:
        """Get task name."""
        return "Async Metadata Retrieval"

    def get_progress_message(self) -> str:
        """Get progress message."""
        return f"Retrieving metadata for {len(self.files)} files"


class AsyncConcreteGroupedMetadataRetrievalTask(WorkerTask):
    """Async task for retrieving metadata from TMDB on a group basis.

    This task groups files by their parsed title and searches TMDB once per group,
    then applies the metadata to all files in the group. This is more efficient
    than searching for each file individually.
    """

    def __init__(
        self,
        groups: list[FileGroup],
        api_key: str,
        progress_callback: Callable | None = None,
    ) -> None:
        """Initialize the async grouped metadata retrieval task.

        Args:
            groups: List of file groups to get metadata for
            api_key: TMDB API key
            progress_callback: Optional callback for progress updates
        """
        self.groups = groups
        self.api_key = api_key
        self.progress_callback = progress_callback
        self._collected_metadata: list[TMDBAnime] = []

    async def execute_async(self) -> list[FileGroup]:
        """Execute the async grouped metadata retrieval.

        Returns:
            List of groups with metadata applied
        """
        logger.debug(f"Starting async grouped metadata retrieval for {len(self.groups)} groups")

        try:
            # Process groups concurrently
            tasks = [self._process_group_async(group) for group in self.groups]

            # Execute all group processing tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            processed_groups = []
            for i, result in enumerate(results):
                group = self.groups[i]

                if isinstance(result, Exception):
                    logger.warning(
                        f"Failed to process group {group.representative_title}: {result}"
                    )
                    processed_groups.append(group)
                else:
                    processed_groups.append(result)

                # Update progress if callback provided
                if self.progress_callback:
                    progress = int((len(processed_groups) / len(self.groups)) * 100)
                    self.progress_callback(progress, len(self.groups))

            logger.info(
                f"Async grouped metadata retrieval completed: {len(processed_groups)} groups processed"
            )
            return processed_groups

        except Exception as e:
            log_operation_error("async grouped metadata retrieval", e, exc_info=True)
            raise

    async def _process_group_async(self, group: FileGroup) -> FileGroup:
        """Process a single group to retrieve and apply metadata.

        Args:
            group: FileGroup to process

        Returns:
            FileGroup with metadata applied
        """
        try:
            representative_title = self._get_representative_title(group)

            if not representative_title:
                logger.debug(
                    f"No representative title found for group with {len(group.files)} files"
                )
                return group

            logger.info(f"Searching TMDB for group '{representative_title}'")

            async with async_tmdb_client_context() as tmdb_client:
                # Search once for this group using comprehensive search
                search_results = await tmdb_client.search_comprehensive(representative_title)

                if search_results:
                    # Use the first (best) result
                    best_result = search_results[0]
                    tmdb_info = TMDBAnime.from_dict(best_result)

                    # Apply metadata to the group
                    self._apply_tmdb_metadata_to_group(group, tmdb_info)

                    display_title = (
                        tmdb_info.title or tmdb_info.original_title or representative_title
                    )
                    logger.info(
                        f"Found TMDB metadata for group '{representative_title}': {display_title}"
                    )

                    # Update group name to match TMDB title
                    if tmdb_info.title:
                        group.representative_title = tmdb_info.title
                        logger.info(
                            f"Updated group name to '{tmdb_info.title}' and applied TMDB metadata to {len(group.files)} files"
                        )
                else:
                    logger.info(f"No TMDB results found for group '{representative_title}'")

        except Exception as e:
            logger.warning(f"Error processing group {group.representative_title}: {e}")

        return group

    def _get_representative_title(self, group: FileGroup) -> str | None:
        """Get the most representative title from a group for TMDB search.

        Args:
            group: FileGroup to get title from

        Returns:
            Representative title string or None if not found
        """
        if not group.files:
            return None

        # Try to find a file with parsed info
        for file in group.files:
            if file.parsed_info and file.parsed_info.title:
                return file.parsed_info.title

        # Fallback to group's representative title
        return group.representative_title

    def _apply_tmdb_metadata_to_group(self, group: FileGroup, tmdb_info: TMDBAnime) -> None:
        """Apply TMDB metadata to a group and its files.

        Args:
            group: FileGroup to apply metadata to
            tmdb_info: TMDBAnime object with metadata
        """
        display_title = tmdb_info.title or tmdb_info.original_title or group.representative_title
        logger.info(f"Applying TMDB metadata to group: {display_title}")

        # Apply metadata to all files in the group
        for file in group.files:
            file.tmdb_info = tmdb_info

        # Update group representative title
        if tmdb_info.title:
            group.representative_title = tmdb_info.title

        logger.info(
            f"Updated group name to '{tmdb_info.title}' and applied TMDB metadata to {len(group.files)} files"
        )

    def execute(self) -> list[FileGroup]:
        """Execute the task synchronously by running the async method.

        Returns:
            List of groups with metadata applied
        """
        return asyncio.run(self.execute_async())

    def get_name(self) -> str:
        """Get task name."""
        return "Async Grouped Metadata Retrieval"

    def get_progress_message(self) -> str:
        """Get progress message."""
        return f"Retrieving metadata for {len(self.groups)} groups"


class AsyncConcreteFileScanningTask(WorkerTask):
    """Async task for scanning directories for anime files."""

    def __init__(
        self,
        scan_directories: list[str],
        supported_extensions: list[str],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> None:
        """Initialize the async file scanning task.

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

    async def execute_async(self) -> list[AnimeFile]:
        """Execute the async file scanning.

        Returns:
            List of found anime files
        """
        logger.debug(f"Starting async file scanning in {len(self.scan_directories)} directories")

        try:
            # Initialize file scanner
            self._file_scanner = FileScanner()

            # Perform scanning
            self._result = self._file_scanner.scan_directory(Path(self.scan_directories[0]))

            logger.info(
                f"Async file scanning completed: {self._result.supported_files} files found"
            )
            return self._result.files

        except Exception as e:
            log_operation_error("async file scanning", e, exc_info=True)
            raise

    def execute(self) -> list[AnimeFile]:
        """Execute the task synchronously by running the async method.

        Returns:
            List of found anime files
        """
        return asyncio.run(self.execute_async())

    def get_name(self) -> str:
        """Get task name."""
        return "Async File Scanning"

    def get_progress_message(self) -> str:
        """Get progress message."""
        return f"Scanning {len(self.scan_directories)} directories for anime files"

    def get_result(self) -> ScanResult | None:
        """Get the scan result."""
        return self._result


# Factory functions for backward compatibility
def create_async_metadata_retrieval_task(
    files: list[AnimeFile], api_key: str, progress_callback: Callable | None = None
) -> AsyncConcreteMetadataRetrievalTask:
    """Create an async metadata retrieval task.

    Args:
        files: List of files to get metadata for
        api_key: TMDB API key
        progress_callback: Optional callback for progress updates

    Returns:
        AsyncConcreteMetadataRetrievalTask instance
    """
    return AsyncConcreteMetadataRetrievalTask(files, api_key, progress_callback)


def create_async_grouped_metadata_retrieval_task(
    groups: list[FileGroup], api_key: str, progress_callback: Callable | None = None
) -> AsyncConcreteGroupedMetadataRetrievalTask:
    """Create an async grouped metadata retrieval task.

    Args:
        groups: List of file groups to get metadata for
        api_key: TMDB API key
        progress_callback: Optional callback for progress updates

    Returns:
        AsyncConcreteGroupedMetadataRetrievalTask instance
    """
    return AsyncConcreteGroupedMetadataRetrievalTask(groups, api_key, progress_callback)


def create_async_file_scanning_task(
    scan_directories: list[str],
    supported_extensions: list[str],
    progress_callback: Callable[[int, int], None] | None = None,
) -> AsyncConcreteFileScanningTask:
    """Create an async file scanning task.

    Args:
        scan_directories: List of directories to scan
        supported_extensions: List of supported file extensions
        progress_callback: Optional callback for progress updates

    Returns:
        AsyncConcreteFileScanningTask instance
    """
    return AsyncConcreteFileScanningTask(scan_directories, supported_extensions, progress_callback)
