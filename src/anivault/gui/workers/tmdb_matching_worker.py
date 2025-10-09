"""
TMDB Matching Worker for AniVault GUI

This module contains the worker class that handles background TMDB matching
operations using PySide6's QThread and signal/slot mechanism.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from anivault.core.matching.engine import MatchingEngine
from anivault.core.parser.anitopy_parser import AnitopyParser
from anivault.gui.models import FileItem
from anivault.services.rate_limiter import TokenBucketRateLimiter
from anivault.services.semaphore_manager import SemaphoreManager
from anivault.services.sqlite_cache_db import SQLiteCacheDB
from anivault.services.state_machine import RateLimitStateMachine
from anivault.services.tmdb_client import TMDBClient
from anivault.shared.constants import FileSystem

logger = logging.getLogger(__name__)


class TMDBMatchingWorker(QObject):
    """
    Worker class for TMDB matching operations in the background.

    This class runs in a separate thread and uses signals to communicate
    with the main GUI thread for thread-safe updates during TMDB API calls.
    """

    # Signals for communication with main thread
    matching_started = Signal()
    file_matched = Signal(dict)  # Emits file matching result
    matching_progress = Signal(int)  # Emits progress percentage (0-100)
    matching_finished = Signal(list)  # Emits list of matching results
    matching_error = Signal(str)  # Emits error message
    matching_cancelled = Signal()

    def __init__(self, api_key: str, parent=None):
        """
        Initialize the TMDB matching worker.

        Args:
            api_key: TMDB API key for authentication
            parent: Parent widget
        """
        super().__init__(parent)

        self._cancelled = False
        self._api_key = api_key
        self._files_to_match: list[FileItem] = []

        # Initialize core components
        self._initialize_components()

        logger.debug("TMDBMatchingWorker initialized")

    def _initialize_components(self) -> None:
        """Initialize TMDB client and matching engine components."""
        try:
            # Initialize cache (SQLite DB)
            cache_db_path = Path(FileSystem.CACHE_DIRECTORY) / "tmdb_cache.db"
            self.cache = SQLiteCacheDB(cache_db_path)

            # Initialize rate limiting components
            self.rate_limiter = TokenBucketRateLimiter(
                capacity=50,  # Default rate limit
                refill_rate=50,
            )
            self.semaphore_manager = SemaphoreManager(concurrency_limit=4)
            self.state_machine = RateLimitStateMachine()

            # Initialize TMDB client
            self.tmdb_client = TMDBClient(
                rate_limiter=self.rate_limiter,
                semaphore_manager=self.semaphore_manager,
                state_machine=self.state_machine,
            )

            # Initialize matching engine
            self.matching_engine = MatchingEngine(
                cache=self.cache,
                tmdb_client=self.tmdb_client,
            )

            # Initialize parser
            self.parser = AnitopyParser()

            logger.debug("TMDB components initialized successfully")

        except Exception:
            logger.exception("Failed to initialize TMDB components: %s")
            raise

    def match_files(self, files: list[FileItem]) -> None:
        """
        Start TMDB matching process for the given files.

        Args:
            files: List of FileItem objects to match against TMDB
        """
        if not files:
            self.matching_error.emit("No files provided for matching")
            return

        self._files_to_match = files.copy()
        self._cancelled = False

        logger.info("Starting TMDB matching for %d files", len(files))
        self.matching_started.emit()

        try:
            # Run the async matching process
            asyncio.run(self._match_files_async())

        except Exception as e:
            logger.exception("Error during TMDB matching: %s")
            self.matching_error.emit(f"TMDB matching error: {e!s}")

    async def _match_files_async(self) -> None:
        """Async implementation of file matching process (optimized group-based)."""
        if not self._files_to_match:
            return

        total_files = len(self._files_to_match)
        matching_results = []
        matched_count = 0

        try:
            # Group files by anime title to reduce duplicate TMDB searches
            groups = self._group_files_by_title(self._files_to_match)
            logger.info(
                "Grouped %d files into %d unique titles",
                total_files,
                len(groups),
            )

            processed_files = 0

            # Match once per group instead of per file
            for file_items in groups.values():
                if self._cancelled:
                    self.matching_cancelled.emit()
                    return

                # Match first file in group to get TMDB result
                first_file = file_items[0]
                group_match_result = await self._match_single_file(first_file)
                match_result = group_match_result.get("match_result")

                # Apply same match result to all files in group
                for file_item in file_items:
                    result = {
                        "file_path": str(file_item.file_path),
                        "file_name": file_item.file_name,
                        "match_result": match_result,
                        "status": "matched" if match_result else "failed",
                    }
                    matching_results.append(result)

                    # Update matched count
                    if match_result is not None:
                        matched_count += 1

                    # Emit file matched signal for each file
                    self.file_matched.emit(result)

                    processed_files += 1

                    # Emit progress signal
                    progress = int(processed_files * 100 / total_files)
                    self.matching_progress.emit(progress)

                    # Allow GUI to process events
                    QApplication.processEvents()

            # Emit completion signal
            self.matching_finished.emit(matching_results)
            logger.info(
                "TMDB matching completed: %d/%d files matched (searched %d unique titles)",
                matched_count,
                total_files,
                len(groups),
            )

        except Exception as e:
            logger.exception("Error in async matching process: %s")
            self.matching_error.emit(f"Async matching error: {e!s}")

    def _group_files_by_title(self, files: list[FileItem]) -> dict[str, list[FileItem]]:
        """
        Group files by anime title to reduce duplicate TMDB searches.

        Args:
            files: List of FileItem objects

        Returns:
            Dictionary mapping anime title to list of FileItem objects
        """
        groups: dict[str, list[FileItem]] = {}

        for file_item in files:
            try:
                # Parse filename to extract title
                parsing_result = self.parser.parse(file_item.file_name)

                if parsing_result:
                    # Use anime title as group key
                    title = (
                        getattr(parsing_result, "title", None) or file_item.file_name
                    )

                    # Normalize title for grouping (lowercase, strip)
                    normalized_title = title.lower().strip()

                    if normalized_title not in groups:
                        groups[normalized_title] = []
                    groups[normalized_title].append(file_item)
                else:
                    # Failed to parse - use filename as group
                    groups[file_item.file_name] = [file_item]

            except Exception as e:  # noqa: BLE001 - GUI file grouping error fallback
                logger.warning("Failed to group file %s: %s", file_item.file_name, e)
                # Add to separate group
                groups[file_item.file_name] = [file_item]

        return groups

    async def _match_single_file(self, file_item: FileItem) -> dict[str, Any]:
        """
        Match a single file against TMDB.

        Args:
            file_item: FileItem to match

        Returns:
            Dictionary containing matching result
        """
        try:
            # Parse the filename (not the full path)
            parsing_result = self.parser.parse(file_item.file_name)

            if not parsing_result:
                return {
                    "file_path": str(file_item.file_path),
                    "file_name": file_item.file_name,
                    "error": "Failed to parse filename",
                    "match_result": None,
                }

            # Convert ParsingResult to dict for MatchingEngine
            if hasattr(parsing_result, "to_dict"):
                parsing_dict = parsing_result.to_dict()
            elif isinstance(parsing_result, dict):
                parsing_dict = parsing_result
            else:
                # Convert ParsingResult to dict if needed
                parsing_dict = {
                    "anime_title": getattr(parsing_result, "title", ""),
                    "episode_number": getattr(parsing_result, "episode", ""),
                    "release_group": getattr(parsing_result, "release_group", ""),
                    "video_resolution": getattr(parsing_result, "quality", ""),
                }

            # Match against TMDB (returns MatchResult | None)
            match_result = await self.matching_engine.find_match(parsing_dict)

            # Keep MatchResult as dataclass (no conversion to dict)
            # This preserves type safety throughout the application

            return {
                "file_path": str(file_item.file_path),
                "file_name": file_item.file_name,
                "parsing_result": parsing_result,
                "match_result": match_result,  # MatchResult dataclass or None
                "status": "matched" if match_result else "failed",
            }

        except Exception as e:
            logger.exception("Error matching file %s", file_item.file_name)
            return {
                "file_path": str(file_item.file_path),
                "file_name": file_item.file_name,
                "error": str(e),
                "match_result": None,
                "status": "error",
            }

    def cancel_matching(self) -> None:
        """Cancel the current matching operation."""
        self._cancelled = True
        logger.info("TMDB matching cancellation requested")

    def _validate_api_key(self) -> None:
        """Validate that the API key is properly configured.

        Raises:
            SecurityError: If API key is missing or invalid
        """
        from anivault.config.settings import get_config
        from anivault.shared.errors import ErrorCode, SecurityError

        try:
            config = get_config()
            api_key = config.tmdb.api_key

            if not api_key or len(api_key.strip()) == 0:
                raise SecurityError(
                    code=ErrorCode.MISSING_CONFIG,
                    message="TMDB API key not configured in settings",
                    context={
                        "operation": "validate_api_key",
                        "worker": "tmdb_matching",
                    },
                )

            if len(api_key) < 10:  # Basic validation
                raise SecurityError(
                    code=ErrorCode.INVALID_CONFIG,
                    message=f"TMDB API key appears invalid (too short: {len(api_key)} characters)",
                    context={
                        "operation": "validate_api_key",
                        "key_length": len(api_key),
                    },
                )

        except SecurityError:
            # Re-raise SecurityError as-is
            raise
        except Exception as e:
            # Wrap other exceptions in SecurityError
            raise SecurityError(
                code=ErrorCode.CONFIG_ERROR,
                message=f"Failed to validate API key: {e}",
                context={
                    "operation": "validate_api_key",
                    "error_type": type(e).__name__,
                },
                original_error=e,
            ) from e
