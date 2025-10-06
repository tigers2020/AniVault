"""
TMDB Matching Worker for AniVault GUI

This module contains the worker class that handles background TMDB matching
operations using PySide6's QThread and signal/slot mechanism.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from ...core.matching.engine import MatchingEngine
from ...core.parser.anitopy_parser import AnitopyParser
from ...services.rate_limiter import TokenBucketRateLimiter
from ...services.semaphore_manager import SemaphoreManager
from ...services.sqlite_cache_db import SQLiteCacheDB
from ...services.state_machine import RateLimitStateMachine
from ...services.tmdb_client import TMDBClient
from ...shared.constants import FileSystem
from ..models import FileItem

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
        self._files_to_match: List[FileItem] = []

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

        except Exception as e:
            logger.error("Failed to initialize TMDB components: %s", e)
            raise

    def match_files(self, files: List[FileItem]) -> None:
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
            logger.error("Error during TMDB matching: %s", e)
            self.matching_error.emit(f"TMDB matching error: {e!s}")

    async def _match_files_async(self) -> None:
        """Async implementation of file matching process."""
        if not self._files_to_match:
            return

        total_files = len(self._files_to_match)
        matching_results = []
        matched_count = 0

        try:
            for i, file_item in enumerate(self._files_to_match):
                if self._cancelled:
                    self.matching_cancelled.emit()
                    return

                # Process current file
                result = await self._match_single_file(file_item)
                matching_results.append(result)

                # Update matched count
                if result.get("match_result") is not None:
                    matched_count += 1

                # Emit progress signal
                progress = int((i + 1) * 100 / total_files)
                self.matching_progress.emit(progress)

                # Emit file matched signal
                self.file_matched.emit(result)

                # Allow GUI to process events
                QApplication.processEvents()

            # Emit completion signal
            self.matching_finished.emit(matching_results)
            logger.info("TMDB matching completed: %d/%d files matched", matched_count, total_files)

        except Exception as e:
            logger.error("Error in async matching process: %s", e)
            self.matching_error.emit(f"Async matching error: {e!s}")

    async def _match_single_file(self, file_item: FileItem) -> Dict[str, Any]:
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

            # Match against TMDB
            match_result = await self.matching_engine.find_match(parsing_dict)

            return {
                "file_path": str(file_item.file_path),
                "file_name": file_item.file_name,
                "parsing_result": parsing_result,
                "match_result": match_result,
                "status": "matched" if match_result else "failed",
            }

        except Exception as e:
            logger.error("Error matching file %s: %s", file_item.file_name, e)
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

    def _validate_api_key(self) -> bool:
        """
        Validate that the API key is properly configured.
        
        Returns:
            True if API key is valid, False otherwise
        """
        from anivault.config import get_config

        try:
            config = get_config()
            api_key = config.tmdb.api_key

            if not api_key or len(api_key.strip()) == 0:
                logger.warning("No TMDB API key configured")
                return False

            if len(api_key) < 10:  # Basic validation
                logger.warning("TMDB API key appears to be invalid (too short)")
                return False

            return True

        except Exception as e:
            logger.error("Failed to validate API key: %s", e)
            return False
