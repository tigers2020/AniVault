"""File Processing ViewModel for AniVault application.

This module provides the FileProcessingViewModel that orchestrates the file processing
pipeline including scanning, parsing, metadata retrieval, and file moving operations.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt5.QtCore import pyqtSignal, pyqtSlot

from ..core.anime_parser import AnimeParser
from ..core.file_grouper import FileGrouper
from ..core.file_mover import FileMover
from ..core.file_scanner import FileScanner
from ..core.metadata_cache import MetadataCache
from ..core.models import AnimeFile, FileGroup
from ..core.parallel_pipeline_manager import ParallelPipelineManager
from ..core.pipeline_stages import PipelineStage
from ..core.services.file_processing_tasks import (
    ConcreteFileGroupingTask,
    ConcreteFileMovingTask,
    ConcreteFileParsingTask,
    ConcreteFileScanningTask,
    ConcreteGroupBasedMetadataRetrievalTask,
    ConcreteMetadataRetrievalTask,
)
from ..core.tmdb_client import TMDBClient, TMDBConfig
from .base_viewmodel import BaseViewModel

# Logger for this module
logger = logging.getLogger(__name__)


class FileProcessingViewModel(BaseViewModel):
    """ViewModel for orchestrating file processing operations.

    This ViewModel manages the complete file processing pipeline:
    1. File scanning and discovery
    2. File grouping and similarity analysis
    3. Anime information parsing
    4. TMDB metadata retrieval
    5. File organization and moving

    It provides commands and properties that the View can bind to,
    and handles all background processing through the FilePipelineWorker.
    """

    # Additional signals specific to file processing
    files_scanned = pyqtSignal(list)  # List[AnimeFile] - when files are scanned
    files_grouped = pyqtSignal(list)  # List[FileGroup] - when files are grouped
    files_parsed = pyqtSignal(list)  # List[AnimeFile] - when files are parsed
    metadata_retrieved = pyqtSignal(list)  # List[AnimeFile] - when metadata is retrieved
    files_moved = pyqtSignal(list)  # List[AnimeFile] - when files are moved
    processing_pipeline_started = pyqtSignal()  # when full pipeline starts
    processing_pipeline_finished = pyqtSignal(bool)  # success status when pipeline completes

    # TMDB selection signals
    tmdb_selection_requested = pyqtSignal(str, list, object)  # query, results, callback
    tmdb_selection_completed = pyqtSignal(dict)  # selected result

    def __init__(self, parent=None) -> None:
        """Initialize the FileProcessingViewModel.

        Args:
            parent: Parent QObject for Qt object hierarchy
        """
        super().__init__(parent)

        # Model components
        self._file_scanner: FileScanner | None = None
        self._anime_parser: AnimeParser | None = None
        self._tmdb_client: TMDBClient | None = None
        self._metadata_cache: MetadataCache | None = None
        self._file_grouper: FileGrouper | None = None
        self._file_mover: FileMover | None = None

        # Processing state
        self._scanned_files: list[AnimeFile] = []
        self._file_groups: list[FileGroup] = []
        self._processed_files: list[AnimeFile] = []
        self._moved_files: list[AnimeFile] = []
        self._failed_files: list[AnimeFile] = []

        # Configuration
        self._scan_directories: list[str] = []
        self._target_directory: str = ""
        self._tmdb_api_key: str = ""
        self._similarity_threshold: float = 0.75

        # Pipeline state
        self._is_pipeline_running: bool = False
        self._current_pipeline_step: str = ""
        self._auto_chaining_enabled: bool = True  # Enable automatic chaining by default

        logger.debug("FileProcessingViewModel initialized")

    def _setup_commands(self) -> None:
        """Set up available commands for file processing."""
        # File scanning commands
        self.add_command("scan_files", self._scan_files_command)
        self.add_command("scan_directories", self._scan_directories_command)

        # File processing commands
        self.add_command("process_files", self._process_files_command)
        self.add_command("group_files", self._group_files_command)
        self.add_command("parse_files", self._parse_files_command)
        self.add_command("retrieve_metadata", self._retrieve_metadata_command)
        self.add_command("retrieve_group_metadata", self._retrieve_group_metadata_command)

        # File organization commands
        self.add_command("move_files", self._move_files_command)
        self.add_command("organize_files", self._organize_files_command)

        # Pipeline commands
        self.add_command("run_full_pipeline", self._run_full_pipeline_command)
        self.add_command("stop_processing", self._stop_processing_command)

        # Configuration commands
        self.add_command("set_scan_directories", self._set_scan_directories_command)
        self.add_command("set_target_directory", self._set_target_directory_command)
        self.add_command("set_tmdb_api_key", self._set_tmdb_api_key_command)
        self.add_command("set_similarity_threshold", self._set_similarity_threshold_command)

        # Utility commands
        self.add_command("clear_results", self._clear_results_command)
        self.add_command("clear_failed_files", self.clear_failed_files)
        self.add_command("reset_pipeline", self._reset_pipeline_command)

        # Auto chaining control commands
        self.add_command("enable_auto_chaining", lambda: self.set_auto_chaining_enabled(True))
        self.add_command("disable_auto_chaining", lambda: self.set_auto_chaining_enabled(False))

        logger.debug("File processing commands set up")

    def _setup_properties(self) -> None:
        """Set up initial property values for file processing."""
        # File lists
        self.set_property("scanned_files", [], notify=False)
        self.set_property("file_groups", [], notify=False)
        self.set_property("processed_files", [], notify=False)
        self.set_property("moved_files", [], notify=False)
        self.set_property("failed_files", [], notify=False)

        # Configuration
        self.set_property("scan_directories", [], notify=False)
        self.set_property("target_directory", "", notify=False)
        self.set_property("tmdb_api_key", "", notify=False)
        self.set_property("similarity_threshold", 0.75, notify=False)

        # Processing state
        self.set_property("is_pipeline_running", False, notify=False)
        self.set_property("current_pipeline_step", "", notify=False)
        self.set_property("scan_progress", 0, notify=False)
        self.set_property("processing_status", "Ready", notify=False)
        self.set_property("auto_chaining_enabled", True, notify=False)

        # Statistics
        self.set_property("total_files_scanned", 0, notify=False)
        self.set_property("total_groups_created", 0, notify=False)
        self.set_property("total_files_processed", 0, notify=False)
        self.set_property("total_files_moved", 0, notify=False)

        # Add validation rules
        self.add_validation_rule(
            "similarity_threshold",
            lambda x: 0.0 <= x <= 1.0,
            "Similarity threshold must be between 0.0 and 1.0",
        )

        logger.debug("File processing properties set up")

    def initialize_components(self) -> None:
        """Initialize all model components.

        This method should be called after setting configuration properties
        to initialize the underlying model components.
        """
        try:
            # Initialize file scanner
            self._file_scanner = FileScanner()

            # Initialize anime parser
            self._anime_parser = AnimeParser()

            # Initialize TMDB client if API key is available
            api_key = self.get_property("tmdb_api_key", "")
            if api_key:
                logger.info(
                    f"Initializing TMDB client during component initialization with API key: ***{api_key[-4:]}"
                )
                tmdb_config = TMDBConfig(api_key=api_key)
                self._tmdb_client = TMDBClient(tmdb_config)
                self._tmdb_api_key = api_key  # Keep private attribute in sync
                logger.info("TMDB client initialized successfully during component initialization")
            else:
                logger.warning("TMDB API key not set, metadata retrieval will be disabled")

            # Initialize metadata cache
            self._metadata_cache = MetadataCache()

            # Initialize file grouper
            self._file_grouper = FileGrouper(similarity_threshold=self._similarity_threshold)

            # Initialize file mover
            self._file_mover = FileMover()

            logger.info("All model components initialized successfully")

        except Exception as e:
            error_msg = f"Failed to initialize model components: {e!s}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            raise

    def create_worker(self):
        """Create and configure a new FilePipelineWorker with additional signal connections.

        Returns:
            Configured FilePipelineWorker instance
        """
        # Call parent method to create worker
        worker = super().create_worker()

        # Connect additional signals specific to file processing
        worker.task_finished.connect(self._on_worker_task_finished)

        logger.debug("FileProcessingViewModel worker signals connected")
        return worker

    # Command implementations

    def _scan_files_command(self, directories: list[str]) -> None:
        """Command to scan directories for anime files.

        Args:
            directories: List of directories to scan
        """
        logger.debug(f"_scan_files_command called with directories: {directories}")
        logger.debug(f"_file_scanner is None: {self._file_scanner is None}")

        if not directories:
            logger.error("No directories specified for scanning")
            self.error_occurred.emit("No directories specified for scanning")
            return

        if not self._file_scanner:
            logger.error("File scanner not initialized")
            logger.debug("File scanner not initialized, returning early")
            self.error_occurred.emit("File scanner not initialized")
            return

        logger.debug("Creating worker if it doesn't exist")
        # Create worker if it doesn't exist
        if not self.has_worker():
            logger.debug("Creating new worker")
            self.create_worker()
            logger.debug("Worker created successfully")

        logger.debug("Creating scanning task")
        logger.debug("About to create ConcreteFileScanningTask")
        # Create and add scanning task
        task = ConcreteFileScanningTask(directories, self._get_supported_extensions())
        logger.debug(f"Created task: {task}")
        logger.debug(f"Created task: {task.get_name()}")

        logger.debug("Adding task to worker")
        logger.debug("About to add task to worker")
        self.add_worker_task(task)
        logger.debug("Task added to worker successfully")
        logger.debug("Task added to worker successfully")

        # Start worker if not running
        if not self.is_worker_running():
            logger.debug("Starting worker")
            self.start_worker()
            logger.debug("Worker started successfully")

        logger.info(f"Started scanning {len(directories)} directories")

    def _scan_directories_command(self) -> None:
        """Command to scan configured directories."""
        logger.debug("scan_directories_command called")
        directories = self.get_property("scan_directories", [])
        logger.info(f"Scan directories command called with directories: {directories}")

        if not directories:
            logger.warning("No scan directories configured")
            self.error_occurred.emit("No scan directories configured")
            return

        logger.info(f"Starting scan for {len(directories)} directories")
        logger.debug("Calling _scan_files_command")
        self._scan_files_command(directories)
        logger.debug("_scan_files_command completed")

    def _process_files_command(self, files: list[AnimeFile]) -> None:
        """Command to process a list of files (group, parse, retrieve metadata).

        Args:
            files: List of files to process
        """
        if not files:
            self.error_occurred.emit("No files specified for processing")
            return

        # Create processing tasks
        tasks: list[Any] = []

        # Grouping task
        if self._file_grouper:
            tasks.append(ConcreteFileGroupingTask(files, self._similarity_threshold))

        # Parsing task
        if self._anime_parser:
            tasks.append(ConcreteFileParsingTask(files))

        # Metadata retrieval task
        api_key = self.get_property("tmdb_api_key", "")
        if self._tmdb_client and api_key:
            tasks.append(ConcreteMetadataRetrievalTask(files, api_key))

        if not tasks:
            self.error_occurred.emit("No processing components available")
            return

        # Create worker if it doesn't exist
        if not self.has_worker():
            self.create_worker()

        # Add tasks to worker
        self.add_worker_tasks(tasks)

        # Start worker if not running
        if not self.is_worker_running():
            self.start_worker()

        logger.info(f"Started processing {len(files)} files")

    def _group_files_command(self, files: list[AnimeFile]) -> None:
        """Command to group similar files.

        Args:
            files: List of files to group
        """
        if not self._file_grouper:
            self.error_occurred.emit("File grouper not initialized")
            return

        if not files:
            self.error_occurred.emit("No files specified for grouping")
            return

        # Create worker if it doesn't exist
        if not self.has_worker():
            self.create_worker()

        task = ConcreteFileGroupingTask(files, self._similarity_threshold)
        self.add_worker_task(task)

        if not self.is_worker_running():
            self.start_worker()

        logger.info(f"Started grouping {len(files)} files")

    def _parse_files_command(self, files: list[AnimeFile]) -> None:
        """Command to parse anime information from files.

        Args:
            files: List of files to parse
        """
        if not self._anime_parser:
            self.error_occurred.emit("Anime parser not initialized")
            return

        if not files:
            self.error_occurred.emit("No files specified for parsing")
            return

        # Create worker if it doesn't exist
        if not self.has_worker():
            self.create_worker()

        task = ConcreteFileParsingTask(files)
        self.add_worker_task(task)

        if not self.is_worker_running():
            self.start_worker()

        logger.info(f"Started parsing {len(files)} files")

    def _retrieve_metadata_command(self, files: list[AnimeFile]) -> None:
        """Command to retrieve metadata from TMDB.

        Args:
            files: List of files to get metadata for
        """
        if not files:
            self.error_occurred.emit("No files specified for metadata retrieval")
            return

        # Check if TMDB client is available
        api_key = self.get_property("tmdb_api_key", "")
        if not self._tmdb_client or not api_key:
            logger.warning(
                "TMDB client not initialized or API key not set - skipping metadata retrieval"
            )
            self.set_property("current_pipeline_step", "Metadata Retrieval Skipped")
            # Emit signal that metadata retrieval is complete (with no metadata)
            self._handle_metadata_result(files)
            return

        # Create worker if it doesn't exist
        if not self.has_worker():
            self.create_worker()

        task = ConcreteMetadataRetrievalTask(files, api_key)
        self.add_worker_task(task)

        if not self.is_worker_running():
            self.start_worker()

        logger.info(f"Started metadata retrieval for {len(files)} files")

    def _retrieve_group_metadata_command(self, groups: list[FileGroup]) -> None:
        """Command to retrieve metadata from TMDB for groups.

        Args:
            groups: List of file groups to get metadata for
        """
        if not groups:
            self.error_occurred.emit("No groups specified for metadata retrieval")
            return

        # Check if TMDB client is available
        api_key = self.get_property("tmdb_api_key", "")
        if not self._tmdb_client or not api_key:
            logger.warning(
                "TMDB client not initialized or API key not set - skipping group metadata retrieval"
            )
            self.set_property("current_pipeline_step", "Metadata Retrieval Skipped")
            # Emit signal that metadata retrieval is complete (with no metadata)
            all_files = []
            for group in groups:
                all_files.extend(group.files)
            self._handle_metadata_result(all_files)
            return

        # Create worker if it doesn't exist
        if not self.has_worker():
            self.create_worker()

        task = ConcreteGroupBasedMetadataRetrievalTask(groups, api_key)
        task.set_viewmodel(self)  # Set ViewModel reference for signal communication
        self.add_worker_task(task)

        if not self.is_worker_running():
            self.start_worker()

        logger.info(f"Started group-based metadata retrieval for {len(groups)} groups")

    def _move_files_command(self, groups: list[FileGroup]) -> None:
        """Command to move and organize files.

        Args:
            groups: List of file groups to move
        """
        if not self._file_mover:
            self.error_occurred.emit("File mover not initialized")
            return

        if not groups:
            self.error_occurred.emit("No file groups specified for moving")
            return

        target_dir = self.get_property("target_directory", "")
        if not target_dir:
            self.error_occurred.emit("Target directory not configured")
            return

        # Create worker if it doesn't exist
        if not self.has_worker():
            self.create_worker()

        task = ConcreteFileMovingTask(groups, target_dir)
        self.add_worker_task(task)

        if not self.is_worker_running():
            self.start_worker()

        logger.info(f"Started moving {len(groups)} file groups")

    def _organize_files_command(self) -> None:
        """Command to organize files using current groups."""
        groups = self.get_property("file_groups", [])
        if not groups:
            self.error_occurred.emit("No file groups available for organization")
            return

        self._move_files_command(groups)

    def _run_full_pipeline_command(self) -> None:
        """Command to run the complete file processing pipeline with parallel execution."""
        directories = self.get_property("scan_directories", [])
        if not directories:
            self.error_occurred.emit("No scan directories configured")
            return

        target_dir = self.get_property("target_directory", "")
        if not target_dir:
            self.error_occurred.emit("Target directory not configured")
            return

        # Set pipeline state
        self.set_property("is_pipeline_running", True)
        self.set_property("current_pipeline_step", "Initializing Parallel Pipeline")
        self.processing_pipeline_started.emit()

        try:
            # Create parallel pipeline manager
            pipeline_manager = ParallelPipelineManager(max_workers=4)

            # Define pipeline tasks with dependencies
            self._setup_pipeline_tasks(pipeline_manager, directories, target_dir)

            # Execute the pipeline
            logger.info("Starting parallel file processing pipeline")
            results = pipeline_manager.execute_pipeline()

            # Handle final results
            self._handle_pipeline_completion(results)

        except Exception as e:
            logger.error(f"Parallel pipeline execution failed: {e}", exc_info=True)
            self.error_occurred.emit(f"Pipeline execution failed: {e}")
            self.set_property("is_pipeline_running", False)
            self.set_property("current_pipeline_step", "Failed")

    def _setup_pipeline_tasks(
        self, 
        pipeline_manager: ParallelPipelineManager, 
        directories: list[str], 
        target_dir: str
    ) -> None:
        """Setup pipeline tasks with their dependencies and handlers.
        
        Args:
            pipeline_manager: The parallel pipeline manager
            directories: List of directories to scan
            target_dir: Target directory for file organization
        """
        # 1. File scanning (no dependencies)
        pipeline_manager.add_task_definition(
            stage=PipelineStage.SCANNING,
            task_factory=lambda: ConcreteFileScanningTask(directories, self._get_supported_extensions()),
            dependencies=set(),
            result_handler=self._handle_scanning_result,
        )

        # 2. File grouping (depends on scanning)
        pipeline_manager.add_task_definition(
            stage=PipelineStage.GROUPING,
            task_factory=lambda: ConcreteFileGroupingTask(self._scanned_files, self._similarity_threshold),
            dependencies={PipelineStage.SCANNING},
            result_handler=self._handle_grouping_result,
        )

        # 3. File parsing (depends on grouping, can run in parallel with metadata retrieval)
        pipeline_manager.add_task_definition(
            stage=PipelineStage.PARSING,
            task_factory=lambda: ConcreteFileParsingTask(self._get_files_from_groups()),
            dependencies={PipelineStage.GROUPING},
            result_handler=self._handle_parsing_result,
        )

        # 4. Group-based metadata retrieval (depends on grouping, can run in parallel with parsing)
        pipeline_manager.add_task_definition(
            stage=PipelineStage.GROUP_METADATA_RETRIEVAL,
            task_factory=lambda: ConcreteGroupBasedMetadataRetrievalTask(
                self._file_groups, 
                self.get_property("tmdb_api_key", "")
            ),
            dependencies={PipelineStage.GROUPING},
            result_handler=self._handle_group_metadata_result,
        )

        # 5. File moving (depends on metadata retrieval)
        pipeline_manager.add_task_definition(
            stage=PipelineStage.FILE_MOVING,
            task_factory=lambda: ConcreteFileMovingTask(self._file_groups, target_dir),
            dependencies={PipelineStage.GROUP_METADATA_RETRIEVAL},
            result_handler=self._handle_moving_result,
        )

    def _get_files_from_groups(self) -> list[AnimeFile]:
        """Get all files from the current file groups.
        
        Returns:
            List of all files from groups
        """
        all_files = []
        for group in self._file_groups:
            all_files.extend(group.files)
        return all_files

    def _handle_pipeline_completion(self, results: dict[PipelineStage, Any]) -> None:
        """Handle the completion of the parallel pipeline.
        
        Args:
            results: Dictionary mapping stage names to their results
        """
        logger.info("Parallel pipeline completed successfully")
        self.set_property("is_pipeline_running", False)
        self.set_property("current_pipeline_step", "Completed")
        
        # Emit final signals based on results
        if PipelineStage.FILE_MOVING in results:
            self.files_moved.emit(results[PipelineStage.FILE_MOVING])
        
        logger.info("Parallel pipeline execution completed")

    def _stop_processing_command(self) -> None:
        """Command to stop current processing."""
        if self.is_worker_running():
            self.stop_worker()
            self.set_property("is_pipeline_running", False)
            self.set_property("current_pipeline_step", "Stopped")
            logger.info("Processing stopped by user")
        else:
            logger.warning("No processing currently running")

    def _set_scan_directories_command(self, directories: list[str]) -> None:
        """Command to set scan directories.

        Args:
            directories: List of directory paths to scan
        """
        print(f"DEBUG: set_scan_directories_command called with: {directories}")  # 강제 출력
        logger.debug(f"set_scan_directories_command called with: {directories}")

        # Validate directories
        valid_dirs = []
        print(
            f"DEBUG: Starting directory validation for {len(directories)} directories"
        )  # 강제 출력
        for i, directory in enumerate(directories):
            print(f"DEBUG: Validating directory {i+1}/{len(directories)}: {directory}")  # 강제 출력
            logger.debug(f"Validating directory: {directory}")
            try:
                path = Path(directory)
                print(f"DEBUG: Path object created: {path}")  # 강제 출력
                exists = path.exists()
                print(f"DEBUG: Path exists: {exists}")  # 강제 출력
                is_dir = path.is_dir()
                print(f"DEBUG: Path is_dir: {is_dir}")  # 강제 출력
                if exists and is_dir:
                    abs_path = str(path.absolute())
                    valid_dirs.append(abs_path)
                    print(f"DEBUG: Valid directory: {directory} -> {abs_path}")  # 강제 출력
                    logger.debug(f"Valid directory: {directory}")
                else:
                    print(
                        f"DEBUG: Invalid directory: {directory} (exists={exists}, is_dir={is_dir})"
                    )  # 강제 출력
                    logger.warning(f"Invalid directory: {directory}")
            except Exception as e:
                print(f"DEBUG: Error validating directory {directory}: {e}")  # 강제 출력
                logger.error(f"Error validating directory {directory}: {e}")

        print(f"DEBUG: Validation complete. Valid directories: {valid_dirs}")  # 강제 출력
        if not valid_dirs:
            print("DEBUG: No valid directories provided")  # 강제 출력
            logger.error("No valid directories provided")
            self.error_occurred.emit("No valid directories provided")
            return

        print(f"DEBUG: Setting scan_directories property to: {valid_dirs}")  # 강제 출력
        logger.debug(f"Setting scan_directories property to: {valid_dirs}")
        self.set_property("scan_directories", valid_dirs)
        self._scan_directories = valid_dirs
        print("DEBUG: Properties set successfully")  # 강제 출력
        logger.info(f"Set scan directories: {valid_dirs}")
        print("DEBUG: set_scan_directories_command completed successfully")  # 강제 출력
        logger.debug("set_scan_directories_command completed successfully")

    def _set_target_directory_command(self, directory: str) -> None:
        """Command to set target directory.

        Args:
            directory: Target directory path
        """
        path = Path(directory)
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created target directory: {directory}")
            except Exception as e:
                self.error_occurred.emit(f"Failed to create target directory: {e!s}")
                return
        elif not path.is_dir():
            self.error_occurred.emit("Target path is not a directory")
            return

        self.set_property("target_directory", str(path.absolute()))
        self._target_directory = str(path.absolute())
        logger.info(f"Set target directory: {directory}")

    def _set_tmdb_api_key_command(self, api_key: str) -> None:
        """Command to set TMDB API key.

        Args:
            api_key: TMDB API key
        """
        if not api_key or not api_key.strip():
            self.error_occurred.emit("API key cannot be empty")
            return

        self.set_property("tmdb_api_key", api_key.strip())
        self._tmdb_api_key = api_key.strip()

        # Reinitialize TMDB client with new key
        if self._tmdb_api_key:
            try:
                logger.info(f"Initializing TMDB client with API key: ***{self._tmdb_api_key[-4:]}")
                tmdb_config = TMDBConfig(api_key=self._tmdb_api_key)
                self._tmdb_client = TMDBClient(tmdb_config)
                logger.info("TMDB client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to reinitialize TMDB client: {e}")
                self.error_occurred.emit(f"Failed to initialize TMDB client: {e!s}")

        logger.info("TMDB API key set")

    def _set_similarity_threshold_command(self, threshold: float) -> None:
        """Command to set similarity threshold for file grouping.

        Args:
            threshold: Similarity threshold (0.0-1.0)
        """
        if not (0.0 <= threshold <= 1.0):
            self.error_occurred.emit("Similarity threshold must be between 0.0 and 1.0")
            return

        self.set_property("similarity_threshold", threshold)
        self._similarity_threshold = threshold

        # Update file grouper if it exists
        if self._file_grouper:
            self._file_grouper.similarity_threshold = threshold

        logger.info(f"Set similarity threshold: {threshold}")

    def _clear_results_command(self) -> None:
        """Command to clear all processing results."""
        self.set_property("scanned_files", [])
        self.set_property("file_groups", [])
        self.set_property("processed_files", [])
        self.set_property("moved_files", [])
        self.set_property("failed_files", [])

        self._scanned_files.clear()
        self._file_groups.clear()
        self._processed_files.clear()
        self._moved_files.clear()
        self._failed_files.clear()

        # Reset statistics
        self.set_property("total_files_scanned", 0)
        self.set_property("total_groups_created", 0)
        self.set_property("total_files_processed", 0)
        self.set_property("total_files_moved", 0)

        logger.info("Cleared all processing results")

    def _reset_pipeline_command(self) -> None:
        """Command to reset the processing pipeline."""
        self._stop_processing_command()
        self._clear_results_command()

        self.set_property("is_pipeline_running", False)
        self.set_property("current_pipeline_step", "")
        self.set_property("processing_status", "Ready")

        logger.info("Reset processing pipeline")

    # Worker signal handlers

    @pyqtSlot(str)
    def _on_worker_task_started(self, task_name: str) -> None:
        """Handle worker task started signal.

        Args:
            task_name: Name of the started task
        """
        self.set_property("current_pipeline_step", task_name)
        self.set_property("processing_status", f"Running: {task_name}")
        logger.debug(f"Worker task started: {task_name}")

    @pyqtSlot(str, int)
    def _on_worker_task_progress(self, task_name: str, progress: int) -> None:
        """Handle worker task progress signal.

        Args:
            task_name: Name of the task
            progress: Progress percentage (0-100)
        """
        self.set_property("scan_progress", progress)
        self.set_property("processing_status", f"{task_name}: {progress}%")
        logger.debug(f"Worker task progress: {task_name} - {progress}%")

    @pyqtSlot(str, object, bool)
    def _on_worker_task_finished(self, task_name: str, result: Any, success: bool) -> None:
        """Handle worker task finished signal.

        Args:
            task_name: Name of the finished task
            result: Task result
            success: Whether the task succeeded
        """
        logger.info(
            f"Worker task finished: {task_name}, success: {success}, result type: {type(result)}"
        )

        if not success:
            logger.error(f"Worker task failed: {task_name}")
            self.error_occurred.emit(f"작업 실패: {task_name}")
            return

        # Process result based on task type
        try:
            logger.debug(f"Task result type: {type(result)}, is list: {isinstance(result, list)}")
            if task_name == "File Scanning" and isinstance(result, list):
                logger.info(f"Processing File Scanning result with {len(result)} files")
                self._handle_scanning_result(result)
            elif task_name == "File Scanning":
                logger.warning(f"File Scanning result is not a list: {type(result)}")
                # Try to handle it anyway if it's iterable
                if hasattr(result, "__iter__"):
                    logger.info(
                        f"Processing File Scanning result (iterable) with {len(list(result))} files"
                    )
                    self._handle_scanning_result(list(result))
            elif task_name == "File Grouping" and isinstance(result, list):
                self._handle_grouping_result(result)
            elif task_name == "File Parsing" and isinstance(result, list):
                self._handle_parsing_result(result)
            elif task_name == "Metadata Retrieval" and isinstance(result, list):
                self._handle_metadata_result(result)
            elif task_name == "Group-based Metadata Retrieval" and isinstance(result, list):
                self._handle_group_metadata_result(result)
            elif task_name == "File Moving" and isinstance(result, list):
                self._handle_moving_result(result)
            else:
                logger.warning(f"Unknown task type or result format: {task_name}")
        except Exception as e:
            logger.error(f"Error processing task result for {task_name}: {e}")
            self.error_occurred.emit(f"결과 처리 오류: {task_name} - {e!s}")

        logger.debug(f"Worker task finished: {task_name}")

    @pyqtSlot(str, str)
    def _on_worker_task_error(self, task_name: str, error_message: str) -> None:
        """Handle worker task error signal.

        Args:
            task_name: Name of the task that failed
            error_message: Error message
        """
        self.error_occurred.emit(f"{task_name} failed: {error_message}")
        logger.error(f"Worker task error: {task_name} - {error_message}")

        # Track failed files based on the task type
        self._track_failed_files(task_name, error_message)

    @pyqtSlot()
    def _on_worker_finished(self) -> None:
        """Handle worker finished signal."""
        self.set_property("is_pipeline_running", False)
        self.set_property("current_pipeline_step", "")
        self.set_property("processing_status", "Completed")
        self.processing_pipeline_finished.emit(True)
        logger.info("Worker finished all tasks")

    # Result handlers

    def _handle_scanning_result(self, files: list[AnimeFile]) -> None:
        """Handle file scanning result."""
        logger.info(f"Handling scanning result: {len(files)} files found")

        self._scanned_files = files
        self.set_property("scanned_files", files)
        self.set_property("total_files_scanned", len(files))
        self.set_property("current_pipeline_step", "Scanning Complete")

        logger.info("Emitting files_scanned signal")
        self.files_scanned.emit(files)
        logger.info(f"File scanning completed: {len(files)} files found")

        # Automatically start grouping after scanning
        if files and self._auto_chaining_enabled:
            logger.info("Starting automatic file grouping after scan")
            self.set_property("current_pipeline_step", "Starting Grouping")
            self.execute_command("group_files", files)
        elif files:
            logger.info("Auto chaining disabled - file grouping can be started manually")
            self.set_property("current_pipeline_step", "Ready for Grouping")

    def _handle_grouping_result(self, groups: list[FileGroup]) -> None:
        """Handle file grouping result."""
        self._file_groups = groups
        self.set_property("file_groups", groups)
        self.set_property("total_groups_created", len(groups))
        self.set_property("current_pipeline_step", "Grouping Complete")
        self.files_grouped.emit(groups)
        logger.info(f"File grouping completed: {len(groups)} groups created")

        # Automatically start parsing after grouping
        if groups and self._auto_chaining_enabled:
            logger.info("Starting automatic file parsing after grouping")
            self.set_property("current_pipeline_step", "Starting Parsing")

            # Extract all files from groups for parsing
            all_files = []
            for group in groups:
                all_files.extend(group.files)

            logger.info(f"Extracted {len(all_files)} files from {len(groups)} groups for parsing")
            self.execute_command("parse_files", all_files)
        elif groups:
            logger.info("Auto chaining disabled - file parsing can be started manually")
            self.set_property("current_pipeline_step", "Ready for Parsing")

    def _handle_parsing_result(self, files: list[AnimeFile]) -> None:
        """Handle file parsing result."""
        self._processed_files = files
        self.set_property("processed_files", files)
        self.set_property("total_files_processed", len(files))
        self.set_property("current_pipeline_step", "Parsing Complete")
        self.files_parsed.emit(files)
        logger.info(f"File parsing completed: {len(files)} files parsed")

        # Automatically start metadata retrieval after parsing
        if files and self._auto_chaining_enabled:
            logger.info("Starting automatic group-based metadata retrieval after parsing")
            self.set_property("current_pipeline_step", "Starting Metadata Retrieval")
            # Use file groups instead of individual files for optimized metadata retrieval
            groups = self.get_property("file_groups", [])
            if groups:
                self.execute_command("retrieve_group_metadata", groups)
            else:
                logger.warning("No file groups available for metadata retrieval")
                self.set_property("current_pipeline_step", "Ready for Metadata Retrieval")
        elif files:
            logger.info("Auto chaining disabled - metadata retrieval can be started manually")
            self.set_property("current_pipeline_step", "Ready for Metadata Retrieval")

    def _handle_metadata_result(self, files: list[AnimeFile]) -> None:
        """Handle metadata retrieval result."""
        # Update processed files with metadata
        self._processed_files = files
        self.set_property("processed_files", files)
        self.set_property("current_pipeline_step", "Metadata Retrieval Complete")
        self.metadata_retrieved.emit(files)
        logger.info(f"Metadata retrieval completed: {len(files)} files processed")

        # Note: File moving is NOT automatically started here as per user request
        # Users can manually start file moving when ready
        logger.info(
            "Pipeline completed up to metadata retrieval. File moving can be started manually."
        )
        self.set_property("current_pipeline_step", "Ready for File Moving")

    def _handle_group_metadata_result(self, groups: list[FileGroup]) -> None:
        """Handle group-based metadata retrieval result."""
        logger.info(f"Handling group metadata result: {len(groups)} groups processed")

        # Merge groups with the same name after TMDB metadata application
        if self._file_grouper:
            logger.info("Merging groups with identical names...")
            merged_groups = self._file_grouper.merge_groups_by_name(groups)
            logger.info(f"Merged {len(groups)} groups into {len(merged_groups)} groups")
            groups = merged_groups

        # Update file groups with metadata and ensure group names are set
        for group in groups:
            if not group.group_name and group.series_title:
                group.group_name = group.series_title
                logger.info(
                    f"Set group name to '{group.group_name}' for group with {len(group.files)} files"
                )

        self._file_groups = groups
        self.set_property("file_groups", groups)

        # Extract all files from groups for processed files list
        all_files = []
        for group in groups:
            all_files.extend(group.files)

        self._processed_files = all_files
        self.set_property("processed_files", all_files)
        self.set_property("current_pipeline_step", "Metadata Retrieval Complete")

        # Emit metadata retrieved signal with all files
        self.metadata_retrieved.emit(all_files)
        logger.info(
            f"Group-based metadata retrieval completed: {len(all_files)} files in {len(groups)} groups processed"
        )

        # Note: File moving is NOT automatically started here as per user request
        # Users can manually start file moving when ready
        logger.info(
            "Pipeline completed up to metadata retrieval. File moving can be started manually."
        )
        self.set_property("current_pipeline_step", "Ready for File Moving")

    def _handle_moving_result(self, files: list[AnimeFile]) -> None:
        """Handle file moving result."""
        self._moved_files = files
        self.set_property("moved_files", files)
        self.set_property("total_files_moved", len(files))
        self.set_property("current_pipeline_step", "File Moving Complete")
        self.files_moved.emit(files)
        logger.info(f"File moving completed: {len(files)} files moved")

    def _track_failed_files(self, task_name: str, error_message: str) -> None:
        """Track files that failed during processing.

        Args:
            task_name: Name of the task that failed
            error_message: Error message describing the failure
        """
        # For now, we'll create a generic failed file entry
        # In a more sophisticated implementation, we could track specific files
        from ..core.models import AnimeFile

        # Create a placeholder failed file entry
        failed_file = AnimeFile(
            file_path=f"Failed during {task_name}",
            filename=f"Error: {error_message[:50]}...",
            file_size=0,
            file_extension=".error",
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        # Add to failed files list
        self._failed_files.append(failed_file)
        self.set_property("failed_files", self._failed_files)

        logger.warning(f"Tracked failed file for task {task_name}: {error_message}")

    def clear_failed_files(self) -> None:
        """Clear the list of failed files."""
        self._failed_files = []
        self.set_property("failed_files", [])
        logger.info("Cleared failed files list")

    def get_processing_statistics(self) -> dict[str, Any]:
        """Get comprehensive processing statistics.

        Returns:
            Dictionary containing all processing statistics
        """
        return {
            "total_files_scanned": len(self._scanned_files),
            "total_groups_created": len(self._file_groups),
            "total_files_processed": len(self._processed_files),
            "total_files_moved": len(self._moved_files),
            "total_files_failed": len(self._failed_files),
            "pending_files": len(self._scanned_files) - len(self._processed_files),
            "unclassified_files": len(self._scanned_files) - len(self._moved_files),
            "is_pipeline_running": self.get_property("is_pipeline_running", False),
            "current_pipeline_step": self.get_property("current_pipeline_step", ""),
            "processing_status": self.get_property("processing_status", "Ready"),
        }

    # Utility methods

    def _get_supported_extensions(self) -> list[str]:
        """Get list of supported file extensions."""
        return [
            ".mkv",
            ".mp4",
            ".avi",
            ".mov",
            ".wmv",
            ".flv",
            ".webm",
            ".m4v",
            ".3gp",
            ".ogv",
            ".ts",
            ".m2ts",
        ]

    def get_scanned_files(self) -> list[AnimeFile]:
        """Get list of scanned files."""
        return self._scanned_files.copy()

    def get_file_groups(self) -> list[FileGroup]:
        """Get list of file groups."""
        return self._file_groups.copy()

    def get_processed_files(self) -> list[AnimeFile]:
        """Get list of processed files."""
        return self._processed_files.copy()

    def get_moved_files(self) -> list[AnimeFile]:
        """Get list of moved files."""
        return self._moved_files.copy()

    def is_pipeline_running(self) -> bool:
        """Check if processing pipeline is running."""
        return self.get_property("is_pipeline_running", False)  # type: ignore[no-any-return]

    def get_processing_status(self) -> str:
        """Get current processing status."""
        return self.get_property("processing_status", "Ready")  # type: ignore[no-any-return]

    def get_scan_progress(self) -> int:
        """Get current scan progress percentage."""
        return self.get_property("scan_progress", 0)  # type: ignore[no-any-return]

    def set_auto_chaining_enabled(self, enabled: bool) -> None:
        """Enable or disable automatic pipeline chaining."""
        self._auto_chaining_enabled = enabled
        self.set_property("auto_chaining_enabled", enabled)
        logger.info(f"Auto chaining {'enabled' if enabled else 'disabled'}")

    def is_auto_chaining_enabled(self) -> bool:
        """Check if automatic pipeline chaining is enabled."""
        return self._auto_chaining_enabled

    def cleanup(self) -> None:
        """Clean up resources."""
        # Stop any running processing
        if self.is_worker_running():
            self.stop_worker()

        # Clear all data
        self._clear_results_command()

        # Shutdown ThreadExecutorManager to ensure all threads are properly cleaned up
        try:
            from ..core.thread_executor_manager import get_thread_executor_manager
            executor_manager = get_thread_executor_manager()
            executor_manager.shutdown_all(wait=True)
            logger.info("ThreadExecutorManager shutdown completed")
        except Exception as e:
            logger.warning(f"Failed to shutdown ThreadExecutorManager: {e}")

        # Call parent cleanup
        super().cleanup()

        logger.info("FileProcessingViewModel cleaned up")
