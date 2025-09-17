"""Main window for AniVault application."""

import logging

from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..core.dialog_orchestrator import DialogOrchestrator, DialogResult, DialogTaskType
from ..themes.theme_manager import get_theme_manager
from ..viewmodels.base_viewmodel import BaseViewModel
from ..viewmodels.file_processing_vm import FileProcessingViewModel
from .anime_details_panel import AnimeDetailsPanel
from .anime_groups_panel import AnimeGroupsPanel
from .group_files_panel import GroupFilesPanel
from .log_panel import LogPanel
from .result_panel import ResultPanel
from .settings_dialog import SettingsDialog
from .tmdb_selection_dialog import TMDBSelectionDialog
from .work_panel import WorkPanel

# Logger for this module
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main window for AniVault application."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the main window.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("AniVault - Anime Management Application")
        self.setGeometry(100, 100, 1400, 900)

        # Initialize configuration manager
        from ..core.config_manager import get_config_manager

        self.config_manager = get_config_manager()

        # Initialize theme manager
        self.theme_manager = get_theme_manager()

        # Apply theme
        self.theme_manager.apply_theme(self)
        self._current_theme = self.config_manager.get_theme()

        # Initialize ViewModels (placeholder for now)
        self._viewmodels: dict[str, BaseViewModel] = {}
        self._initialize_viewmodels()

        # Initialize dialog orchestrator
        self._dialog_orchestrator = DialogOrchestrator(self)
        self._setup_dialog_orchestrator()

        # Create menu bar
        self._create_menu_bar()

        # Create central widget and layout
        self._create_central_widget()

        # Create status bar
        self._create_status_bar()

        # Connect panels to ViewModels after both are created
        self._connect_panels_to_viewmodels()

        # Connect signals
        self._connect_signals()

        logger.info("MainWindow initialized")

    def _setup_dialog_orchestrator(self) -> None:
        """Setup dialog orchestrator with dialog creators."""
        # Register TMDB selection dialog creator
        self._dialog_orchestrator.register_dialog_creator(
            DialogTaskType.SELECTION, self._create_tmdb_selection_dialog
        )

        # Register manual search dialog creator
        self._dialog_orchestrator.register_dialog_creator(
            DialogTaskType.MANUAL_SEARCH, self._create_manual_search_dialog
        )

        # Connect orchestrator signals
        self._dialog_orchestrator.dialog_completed.connect(self._on_dialog_completed)
        self._dialog_orchestrator.dialog_error.connect(self._on_dialog_error)

        logger.info("Dialog orchestrator setup completed")

    def _create_tmdb_selection_dialog(self, task) -> QDialog:
        """Create TMDB selection dialog for the given task."""
        try:
            # Get TMDB API key from ViewModel
            api_key = self.file_processing_vm.get_property("tmdb_api_key", "")

            # Create dialog
            dialog = TMDBSelectionDialog(self, self.theme_manager, api_key)

            # Set initial search data
            payload = task.payload
            query = payload.get("query", "")
            results = payload.get("results", [])

            dialog.set_initial_search(query, results)

            return dialog

        except Exception as e:
            logger.error(f"Failed to create TMDB selection dialog: {e}")
            return None

    def _create_manual_search_dialog(self, task) -> QDialog:
        """Create manual search dialog for the given task."""
        try:
            # Get TMDB API key from ViewModel
            api_key = self.file_processing_vm.get_property("tmdb_api_key", "")

            # Create dialog
            dialog = TMDBSelectionDialog(self, self.theme_manager, api_key)

            # Set initial search data
            payload = task.payload
            query = payload.get("query", "")

            dialog.set_initial_search(query)

            return dialog

        except Exception as e:
            logger.error(f"Failed to create manual search dialog: {e}")
            return None

    def _on_dialog_completed(self, result: DialogResult) -> None:
        """Handle dialog completion."""
        logger.info(f"Dialog completed: {result.task_id} (success: {result.success})")

        # Get stored callback if exists
        callback = None
        if hasattr(self, "_tmdb_callbacks") and result.task_id in self._tmdb_callbacks:
            callback = self._tmdb_callbacks.pop(result.task_id)

        if result.success and result.result:
            # Handle successful dialog result
            self.log_panel.add_log(f"다이얼로그 완료: {result.task_id}")

            # Call the original callback if it exists
            if callback:
                try:
                    callback(result.result)
                    logger.info(f"Callback executed for task {result.task_id}")
                except Exception as e:
                    logger.error(f"Error executing callback for task {result.task_id}: {e}")
        else:
            # Handle dialog error
            error_msg = result.error or "Unknown error"
            self.log_panel.add_log(f"다이얼로그 오류: {error_msg}")

            # Call callback with None result for error case
            if callback:
                try:
                    callback(None)
                except Exception as e:
                    logger.error(f"Error executing error callback for task {result.task_id}: {e}")

    def _on_dialog_error(self, error: str) -> None:
        """Handle dialog error."""
        logger.error(f"Dialog error: {error}")
        self.log_panel.add_log(f"다이얼로그 오류: {error}")

    def _initialize_viewmodels(self) -> None:
        """Initialize ViewModels for the application."""
        try:
            # Initialize FileProcessingViewModel
            self.file_processing_vm = FileProcessingViewModel(self)
            self.file_processing_vm.initialize()
            self.add_viewmodel("file_processing", self.file_processing_vm)

            # Load configuration and set it in ViewModel
            self._load_configuration_to_viewmodel()

            # Initialize components after ViewModel is ready
            self.file_processing_vm.initialize_components()

            logger.info("ViewModels initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ViewModels: {e}")
            self._on_error_occurred(f"ViewModel 초기화 실패: {str(e)}")

    def _load_configuration_to_viewmodel(self) -> None:
        """Load configuration from config manager and set it in ViewModel."""
        try:
            logger.info("Starting configuration load to ViewModel...")

            # Load TMDB API key
            tmdb_api_key = self.config_manager.get_tmdb_api_key()
            logger.info(
                f"TMDB API key retrieved: {'***' + tmdb_api_key[-4:] if tmdb_api_key else 'None'}"
            )

            if tmdb_api_key:
                self.file_processing_vm.execute_command("set_tmdb_api_key", tmdb_api_key)
                logger.info("TMDB API key set in ViewModel successfully")
            else:
                logger.warning(
                    "No TMDB API key found in configuration - metadata retrieval will be skipped"
                )

            # Load target directory
            target_directory = self.config_manager.get_destination_root()
            logger.info(f"Target directory retrieved: {target_directory or 'None'}")

            if target_directory:
                self.file_processing_vm.execute_command("set_target_directory", target_directory)
                logger.info("Target directory set in ViewModel successfully")

            # Load similarity threshold
            similarity_threshold = self.config_manager.get(
                "application.file_organization.similarity_threshold", 0.75
            )
            logger.info(f"Similarity threshold retrieved: {similarity_threshold}")
            self.file_processing_vm.execute_command(
                "set_similarity_threshold", similarity_threshold
            )
            logger.info("Similarity threshold set in ViewModel successfully")

            # Load scan directories
            scan_directories = self.config_manager.get(
                "application.file_organization.source_directories", []
            )
            logger.info(f"Scan directories retrieved: {scan_directories}")

            if scan_directories:
                self.file_processing_vm.execute_command("set_scan_directories", scan_directories)
                logger.info("Scan directories set in ViewModel successfully")

            logger.info("All configuration loaded successfully to ViewModel")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}", exc_info=True)
            self._on_error_occurred(f"설정 로드 실패: {str(e)}")

    def _connect_panels_to_viewmodels(self) -> None:
        """Connect panels to their ViewModels after both are created."""
        try:
            # Connect panels to ViewModel
            if hasattr(self, "work_panel") and hasattr(self, "file_processing_vm"):
                self.work_panel.set_viewmodel(self.file_processing_vm)
                logger.info("WorkPanel connected to FileProcessingViewModel")

            if hasattr(self, "result_panel") and hasattr(self, "file_processing_vm"):
                self.result_panel.set_viewmodel(self.file_processing_vm)
                logger.info("ResultPanel connected to FileProcessingViewModel")
        except Exception as e:
            logger.error(f"Failed to connect panels to ViewModels: {e}")
            self._on_error_occurred(f"패널 연결 실패: {str(e)}")

    def _connect_signals(self) -> None:
        """Connect signals between UI components and ViewModels."""
        # Connect error handling
        for viewmodel in self._viewmodels.values():
            viewmodel.error_occurred.connect(self._on_error_occurred)
            viewmodel.status_changed.connect(self._on_status_changed)

        # Connect FileProcessingViewModel specific signals
        if hasattr(self, "file_processing_vm"):
            self._connect_file_processing_signals()

        # Connect result panel signals
        if hasattr(self, "result_panel"):
            self.result_panel.file_selected.connect(self._on_file_selected)
            self.result_panel.group_selected.connect(self._on_group_selected)
            self.result_panel.retry_requested.connect(self._on_retry_requested)
            self.result_panel.clear_requested.connect(self._on_clear_requested)

        # Connect anime groups panel signals
        if hasattr(self, "groups_panel"):
            self.groups_panel.group_selected.connect(self._on_group_selected)

    def _connect_file_processing_signals(self) -> None:
        """Connect FileProcessingViewModel signals to UI components."""
        vm = self.file_processing_vm

        # Connect processing signals with error handling
        try:
            vm.files_scanned.connect(self._on_files_scanned)
            vm.files_grouped.connect(self._on_files_grouped)
            vm.files_parsed.connect(self._on_files_parsed)
            vm.metadata_retrieved.connect(self._on_metadata_retrieved)
            vm.files_moved.connect(self._on_files_moved)
            vm.processing_pipeline_started.connect(self._on_pipeline_started)
            vm.processing_pipeline_finished.connect(self._on_pipeline_finished)

            # Connect TMDB selection signals
            vm.tmdb_selection_requested.connect(self._on_tmdb_selection_requested)
            vm.tmdb_selection_completed.connect(self._on_tmdb_selection_completed)

            # Connect worker signals
            vm.worker_task_started.connect(self._on_worker_task_started)
            vm.worker_task_progress.connect(self._on_worker_task_progress)
            vm.worker_task_finished.connect(self._on_worker_task_finished)
            vm.worker_task_error.connect(self._on_worker_task_error)
            vm.worker_finished.connect(self._on_worker_finished)

            # Connect property changes
            vm.property_changed.connect(self._on_property_changed)

            logger.debug("FileProcessingViewModel signals connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect FileProcessingViewModel signals: {e}")
            self._on_error_occurred(f"시그널 연결 실패: {str(e)}")

    @pyqtSlot(str)
    def _on_error_occurred(self, error_message: str) -> None:
        """
        Handle error signals from ViewModels.

        Args:
            error_message: Error message to display
        """
        logger.error(f"Error occurred: {error_message}")

        # Show error message box
        QMessageBox.warning(self, "오류", f"오류가 발생했습니다:\n{error_message}")

        # Add to log panel
        self.log_panel.add_log(f"오류: {error_message}")

        # Update status bar with error indication
        self.statusBar().showMessage(f"오류: {error_message}")

        # Update UI state to show error condition
        # Could disable certain buttons or show error indicators

    @pyqtSlot(str)
    def _on_status_changed(self, status_message: str) -> None:
        """
        Handle status change signals from ViewModels.

        Args:
            status_message: Status message to display
        """
        logger.debug(f"Status changed: {status_message}")
        self.statusBar().showMessage(f"상태: {status_message}")
        self.log_panel.add_log(f"상태: {status_message}")

    @pyqtSlot(str)
    def _on_file_selected(self, file_name: str) -> None:
        """
        Handle file selection from result panel.

        Args:
            file_name: Selected file name
        """
        logger.debug(f"File selected: {file_name}")
        self.log_panel.add_log(f"파일 선택됨: {file_name}")

    @pyqtSlot(str)
    def _on_group_selected(self, group_identifier: str) -> None:
        """
        Handle group selection from result panel.

        Args:
            group_identifier: Selected group ID or name
        """
        logger.debug(f"Group selected: {group_identifier}")
        self.log_panel.add_log(f"그룹 선택됨: {group_identifier}")

        # Find the selected group and display its details
        self._display_group_details(group_identifier)

        # Filter files to show only files from the selected group
        self.result_panel.filter_files_by_group(group_identifier)

    def _display_group_details(self, group_identifier: str) -> None:
        """
        Display details for the selected group.

        Args:
            group_identifier: Group ID or name of the selected group
        """
        logger.debug(f"Displaying details for group: '{group_identifier}'")

        # Get file groups from the ViewModel
        groups = self.file_processing_vm.get_property("file_groups", [])
        logger.debug(f"Available groups: {[(g.group_id, g.series_title) for g in groups]}")

        # Find the selected group by group_id first, then fallback to series_title
        selected_group = None
        for group in groups:
            logger.debug(
                f"Comparing '{group_identifier}' with group_id '{group.group_id}' and series_title '{group.series_title}'"
            )
            if group.group_id == group_identifier or group.series_title == group_identifier:
                selected_group = group
                break

        if selected_group:
            logger.debug(
                f"Found group: {selected_group.series_title} with {len(selected_group.files)} files"
            )
            # Display group details in the details panel
            self.details_panel.display_group_details(selected_group)
            self.log_panel.add_log(f"애니메이션 상세 정보 표시: {selected_group.series_title}")
        else:
            logger.warning(
                f"Group not found: '{group_identifier}'. Available groups: {[g.series_title for g in groups]}"
            )
            # Clear details panel
            self.details_panel.clear_details()
            self.log_panel.add_log(f"그룹을 찾을 수 없음: {group_identifier}")

    @pyqtSlot(str)
    def _on_retry_requested(self, file_name: str) -> None:
        """
        Handle retry request for a file.

        Args:
            file_name: File name to retry
        """
        logger.debug(f"Retry requested for: {file_name}")
        self.log_panel.add_log(f"재시도 요청: {file_name}")

    @pyqtSlot()
    def _on_clear_requested(self) -> None:
        """Handle clear results request."""
        logger.debug("Clear results requested")
        self.log_panel.add_log("결과 지우기 요청됨")
        # Execute clear command on ViewModel
        if hasattr(self, "file_processing_vm"):
            self.file_processing_vm.execute_command("clear_results")

    # FileProcessingViewModel signal handlers

    @pyqtSlot(list)
    def _on_files_scanned(self, files) -> None:
        """Handle files scanned signal."""
        try:
            logger.info(
                f"MainWindow received files_scanned signal with {len(files) if isinstance(files, list) else 'non-list'} items"
            )

            if not isinstance(files, list):
                logger.warning(f"Invalid files data type: {type(files)}")
                return

            logger.info(f"Files scanned: {len(files)} files")
            self.log_panel.add_log(f"파일 스캔 완료: {len(files)}개 파일 발견")

            # Update result panel with scanned files
            if hasattr(self, "result_panel"):
                logger.info("Updating result panel with scanned files")
                self.result_panel.update_files(files)
                logger.info("Result panel updated successfully")
            else:
                logger.warning("Result panel not available")
        except Exception as e:
            logger.error(f"Error handling files scanned signal: {e}")
            self._on_error_occurred(f"파일 스캔 결과 처리 오류: {str(e)}")

    @pyqtSlot(list)
    def _on_files_grouped(self, groups) -> None:
        """Handle files grouped signal."""
        try:
            if not isinstance(groups, list):
                logger.warning(f"Invalid groups data type: {type(groups)}")
                return

            logger.info(f"Files grouped: {len(groups)} groups")
            self.log_panel.add_log(f"파일 그룹화 완료: {len(groups)}개 그룹 생성")

            # Update result panel with groups (for file display)
            if hasattr(self, "result_panel"):
                self.result_panel.update_groups(groups)

            # Update anime groups panel with groups (for group display)
            if hasattr(self, "groups_panel"):
                self.groups_panel.update_groups(groups)
                logger.debug(f"Updated anime groups panel with {len(groups)} groups")
        except Exception as e:
            logger.error(f"Error handling files grouped signal: {e}")
            self._on_error_occurred(f"파일 그룹화 결과 처리 오류: {str(e)}")

    @pyqtSlot(list)
    def _on_files_parsed(self, files) -> None:
        """Handle files parsed signal."""
        logger.info(f"Files parsed: {len(files)} files")
        self.log_panel.add_log(f"파일 파싱 완료: {len(files)}개 파일 처리")

    @pyqtSlot(list)
    def _on_metadata_retrieved(self, files) -> None:
        """Handle metadata retrieved signal."""
        logger.info(f"Metadata retrieved: {len(files)} files")
        self.log_panel.add_log(f"메타데이터 검색 완료: {len(files)}개 파일")

        # Update both panels with updated groups (with metadata)
        groups = self.file_processing_vm.get_property("file_groups", [])
        if groups:
            # Update result panel groups table
            self.result_panel.update_groups(groups)
            logger.debug(
                f"Updated result panel groups after metadata retrieval with {len(groups)} groups"
            )

            # Update anime groups panel
            if hasattr(self, "groups_panel"):
                self.groups_panel.update_groups(groups)
                logger.debug(
                    f"Updated anime groups panel after metadata retrieval with {len(groups)} groups"
                )

    @pyqtSlot(list)
    def _on_files_moved(self, files) -> None:
        """Handle files moved signal."""
        logger.info(f"Files moved: {len(files)} files")
        self.log_panel.add_log(f"파일 이동 완료: {len(files)}개 파일")

    @pyqtSlot(str, list, object)
    def _on_tmdb_selection_requested(self, query: str, results: list, callback) -> None:
        """Handle TMDB selection request using dialog orchestrator."""
        logger.info(f"TMDB selection requested for query: {query}")
        self.log_panel.add_log(f"TMDB 검색 결과 선택 요청: {query}")

        # Store callback for later use
        if not hasattr(self, "_tmdb_callbacks"):
            self._tmdb_callbacks = {}

        # Create coalesce key for the query to prevent duplicate dialogs
        coalesce_key = f"tmdb_selection_{query}"

        # Request dialog through orchestrator
        task_id = self._dialog_orchestrator.request_dialog(
            DialogTaskType.SELECTION,
            payload={"query": query, "results": results, "callback": callback},
            coalesce_key=coalesce_key,
            priority=1,
        )

        # Store callback for this task
        self._tmdb_callbacks[task_id] = callback

        logger.info(f"TMDB selection dialog requested (task_id: {task_id})")

    @pyqtSlot(dict)
    def _on_tmdb_selection_completed(self, result: dict) -> None:
        """Handle TMDB selection completion."""
        logger.info(f"TMDB selection completed: {result.get('name', 'Unknown')}")
        self.log_panel.add_log(f"TMDB 검색 결과 선택 완료: {result.get('name', 'Unknown')}")

    @pyqtSlot()
    def _on_pipeline_started(self) -> None:
        """Handle processing pipeline started signal."""
        logger.info("Processing pipeline started")
        self.log_panel.add_log("처리 파이프라인 시작됨")

        # Update UI state
        if hasattr(self, "work_panel"):
            self.work_panel.set_processing_state(True)

    @pyqtSlot(bool)
    def _on_pipeline_finished(self, success: bool) -> None:
        """Handle processing pipeline finished signal."""
        status = "성공" if success else "실패"
        logger.info(f"Processing pipeline finished: {status}")
        self.log_panel.add_log(f"처리 파이프라인 완료: {status}")

        # Update UI state
        if hasattr(self, "work_panel"):
            self.work_panel.set_processing_state(False)

    @pyqtSlot(str)
    def _on_worker_task_started(self, task_name: str) -> None:
        """Handle worker task started signal."""
        logger.debug(f"Worker task started: {task_name}")
        self.log_panel.add_log(f"작업 시작: {task_name}")

    @pyqtSlot(str, int)
    def _on_worker_task_progress(self, task_name: str, progress: int) -> None:
        """Handle worker task progress signal."""
        logger.debug(f"Worker task progress: {task_name} - {progress}%")

        # Update progress in work panel
        if hasattr(self, "work_panel"):
            self.work_panel.update_progress(progress)

    @pyqtSlot(str, object, bool)
    def _on_worker_task_finished(self, task_name: str, result, success: bool) -> None:
        """Handle worker task finished signal."""
        status = "성공" if success else "실패"
        logger.info(f"Worker task finished: {task_name} - {status}")

    @pyqtSlot(str, str)
    def _on_worker_task_error(self, task_name: str, error_message: str) -> None:
        """Handle worker task error signal."""
        logger.error(f"Worker task error: {task_name} - {error_message}")
        self.log_panel.add_log(f"작업 오류: {task_name} - {error_message}")

    @pyqtSlot()
    def _on_worker_finished(self) -> None:
        """Handle worker finished signal."""
        logger.info("Worker finished all tasks")
        self.log_panel.add_log("모든 작업 완료")

    @pyqtSlot(str, object)
    def _on_property_changed(self, property_name: str, value) -> None:
        """Handle property change signal."""
        try:
            logger.debug(f"Property changed: {property_name} = {value}")

            # Update UI based on property changes
            if property_name == "is_pipeline_running":
                if hasattr(self, "work_panel"):
                    self.work_panel.set_processing_state(bool(value))
            elif property_name == "processing_status":
                self.statusBar().showMessage(f"상태: {value}")
            elif property_name in [
                "scanned_files",
                "file_groups",
                "processed_files",
                "moved_files",
            ]:
                # Update statistics
                self._update_statistics()
        except Exception as e:
            logger.error(f"Error handling property change: {property_name} = {value}, error: {e}")
            # Don't emit error for property changes to avoid infinite loops

    def _update_statistics(self) -> None:
        """Update statistics display based on ViewModel data."""
        if not hasattr(self, "file_processing_vm"):
            return

        vm = self.file_processing_vm

        # Get current data from ViewModel
        scanned_files = vm.get_property("scanned_files", [])
        file_groups = vm.get_property("file_groups", [])
        processed_files = vm.get_property("processed_files", [])
        moved_files = vm.get_property("moved_files", [])

        # Calculate statistics
        total_files = len(scanned_files)
        total_groups = len(file_groups)
        pending_files = total_files - len(processed_files)
        completed_files = len(processed_files)
        unclassified_files = total_files - len(moved_files)
        failed_items = 0  # This would need to be tracked in ViewModel

        # Update statistics cards if they exist
        # Note: The stat cards are created in _create_left_panel but not stored as instance variables
        # For now, just log the statistics - in a real implementation, you'd update the UI elements
        logger.debug(
            f"Statistics updated: {total_files} files, {total_groups} groups, {completed_files} completed, {pending_files} pending"
        )

        # Update status bar with current statistics
        self.statusBar().showMessage(
            f"파일: {total_files}개, 그룹: {total_groups}개, 완료: {completed_files}개"
        )

    def get_viewmodel(self, name: str) -> BaseViewModel | None:
        """
        Get a ViewModel by name.

        Args:
            name: ViewModel name

        Returns:
            ViewModel instance or None if not found
        """
        return self._viewmodels.get(name)

    def add_viewmodel(self, name: str, viewmodel: BaseViewModel) -> None:
        """
        Add a ViewModel to the main window.

        Args:
            name: ViewModel name
            viewmodel: ViewModel instance
        """
        self._viewmodels[name] = viewmodel
        viewmodel.error_occurred.connect(self._on_error_occurred)
        viewmodel.status_changed.connect(self._on_status_changed)
        logger.debug(f"Added ViewModel: {name}")

    def _create_menu_bar(self) -> None:
        """Create the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("파일")
        file_menu.addAction("열기", self._open_files)
        file_menu.addAction("저장", self._save_settings)
        file_menu.addSeparator()
        file_menu.addAction("종료", self.close)

        # Edit menu
        edit_menu = menubar.addMenu("편집")
        edit_menu.addAction("설정", self._open_settings)
        edit_menu.addAction("테마", self._change_theme)

        # View menu
        view_menu = menubar.addMenu("보기")
        view_menu.addAction("전체 화면", self._toggle_fullscreen)
        view_menu.addAction("패널 숨기기", self._toggle_panels)

        # Tools menu
        tools_menu = menubar.addMenu("도구")
        tools_menu.addAction("스캔", self._scan_files)
        tools_menu.addAction("정리", self._organize_files)
        tools_menu.addAction("미리보기", self._preview_organization)

        # Help menu
        help_menu = menubar.addMenu("도움말")
        help_menu.addAction("도움말", self._show_help)
        help_menu.addAction("정보", self._show_about)

    def _create_central_widget(self) -> None:
        """Create the central widget with 4-panel layout."""
        # Create main content widget
        main_content = QWidget()
        main_content.setStyleSheet(
            f"background-color: {self.theme_manager.get_color('bg_primary')};"
        )

        # Main layout
        main_layout = QHBoxLayout(main_content)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Create horizontal splitter for main panels
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setChildrenCollapsible(False)

        # Left panel (Work Panel + Statistics)
        left_panel = self._create_left_panel()
        main_splitter.addWidget(left_panel)

        # Middle panel (Result Panel)
        middle_panel = self._create_middle_panel()
        main_splitter.addWidget(middle_panel)

        # Right panel (Anime Details)
        right_panel = self._create_right_panel()
        main_splitter.addWidget(right_panel)

        # Set splitter proportions
        main_splitter.setSizes([300, 500, 400])

        # Add splitter to main layout
        main_layout.addWidget(main_splitter)

        # Create vertical layout for main content and log
        content_widget = QWidget()
        content_widget.setStyleSheet(
            f"background-color: {self.theme_manager.get_color('bg_primary')};"
        )
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        # Add main content
        content_layout.addWidget(main_content)

        # Add log panel at bottom
        self.log_panel = LogPanel(config_manager=self.config_manager)
        content_layout.addWidget(self.log_panel)

        # Set as central widget
        self.setCentralWidget(content_widget)

    def _create_left_panel(self) -> QWidget:
        """Create the left panel with work controls and statistics."""
        panel = QWidget()
        panel.setMaximumWidth(300)
        panel.setMinimumWidth(250)
        panel.setStyleSheet(f"background-color: {self.theme_manager.get_color('bg_primary')};")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Work panel
        self.work_panel = WorkPanel(config_manager=self.config_manager)
        layout.addWidget(self.work_panel)

        # Note: WorkPanel will be connected to ViewModel after ViewModel initialization

        # Statistics panel
        stats_group = QGroupBox("통계")
        stats_group.setStyleSheet(self.theme_manager.current_theme.get_group_box_style())

        stats_layout = QGridLayout(stats_group)

        # Statistics cards
        stats_data = [
            ("전체 파일", "120", "primary"),
            ("전체 그룹", "15", "secondary"),
            ("대기 파일", "12", "warning"),
            ("완료 파일", "108", "accent"),
            ("미분류 파일", "5", "error"),
            ("실패 항목", "2", "text_muted"),
        ]

        for i, (label, value, color_name) in enumerate(stats_data):
            row = i // 2
            col = i % 2

            stat_widget = self._create_stat_card(label, value, color_name)
            stats_layout.addWidget(stat_widget, row, col)

        layout.addWidget(stats_group)
        layout.addStretch()

        return panel

    def _create_middle_panel(self) -> QWidget:
        """Create the middle panel with result display."""
        panel = QWidget()
        panel.setStyleSheet(f"background-color: {self.theme_manager.get_color('bg_primary')};")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Result panel for displaying processing results
        self.result_panel = ResultPanel(config_manager=self.config_manager)
        layout.addWidget(self.result_panel)

        # Keep the old panels for backward compatibility (hidden by default)
        self.groups_panel = AnimeGroupsPanel()
        self.groups_panel.hide()

        self.files_panel = GroupFilesPanel()
        self.files_panel.hide()

        return panel

    def _create_right_panel(self) -> QWidget:
        """Create the right panel with anime details."""
        panel = QWidget()
        panel.setMaximumWidth(400)
        panel.setMinimumWidth(300)
        panel.setStyleSheet(f"background-color: {self.theme_manager.get_color('bg_primary')};")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Anime details panel
        self.details_panel = AnimeDetailsPanel()
        layout.addWidget(self.details_panel)

        return panel

    def _create_stat_card(self, label: str, value: str, color_name: str) -> QWidget:
        """Create a statistics card widget."""
        card = QFrame()
        card.frame_type = "card"
        card.setStyleSheet(self.theme_manager.current_theme.get_frame_style("card"))

        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)

        # Value label
        value_label = QLabel(value)
        value_label.label_type = "stat_value"
        value_label.setStyleSheet(
            f"""
            QLabel {{
                font-size: 24px;
                font-weight: bold;
                color: {self.theme_manager.get_color(color_name)};
            }}
        """
        )
        value_label.setAlignment(Qt.AlignCenter)

        # Label
        label_widget = QLabel(label)
        label_widget.label_type = "stat_label"
        label_widget.setStyleSheet(self.theme_manager.current_theme.get_label_style("stat_label"))
        label_widget.setAlignment(Qt.AlignCenter)

        layout.addWidget(value_label)
        layout.addWidget(label_widget)

        return card

    def _create_status_bar(self) -> None:
        """Create the status bar."""
        status_bar = QStatusBar()
        status_bar.showMessage("상태: 준비 완료")
        self.setStatusBar(status_bar)

    # Menu action handlers
    def _open_files(self) -> None:
        """Handle open files action."""
        self.log_panel.add_log("파일 열기 대화상자 열림")

    def _save_settings(self) -> None:
        """Handle save settings action."""
        self.log_panel.add_log("설정 저장됨")

    def _open_settings(self) -> None:
        """Handle open settings action."""
        try:
            # Create and show settings dialog
            settings_dialog = SettingsDialog(self, self.config_manager)
            settings_dialog.settings_saved.connect(self._on_settings_saved)

            if settings_dialog.exec_() == QDialog.Accepted:
                self.log_panel.add_log("설정이 저장되었습니다")
            else:
                self.log_panel.add_log("설정 변경이 취소되었습니다")

        except Exception as e:
            logger.error("Failed to open settings dialog: %s", str(e))
            self._on_error_occurred(f"설정 대화상자 열기 실패: {str(e)}")

    def _on_settings_saved(self) -> None:
        """Handle settings saved signal."""
        try:
            # Reload theme if it was changed
            current_theme = self.config_manager.get_theme()
            if hasattr(self, "_current_theme") and self._current_theme != current_theme:
                self.theme_manager.apply_theme(self)
                self._current_theme = current_theme
                self.log_panel.add_log(f"테마가 {current_theme}로 변경되었습니다")

                # Reapply theme to all panels
                self._apply_theme_to_panels()

            # Update other components that might be affected by settings changes
            self._update_components_from_settings()

        except Exception as e:
            logger.error("Failed to handle settings saved: %s", str(e))

    def _apply_theme_to_panels(self) -> None:
        """Apply current theme to all panels."""
        try:
            if hasattr(self, "work_panel"):
                self.work_panel.setStyleSheet(
                    self.theme_manager.current_theme.get_group_box_style()
                )

            if hasattr(self, "result_panel"):
                self.result_panel.setStyleSheet(
                    self.theme_manager.current_theme.get_group_box_style()
                )

            if hasattr(self, "log_panel"):
                self.log_panel.setStyleSheet(self.theme_manager.current_theme.get_group_box_style())

            logger.info("Theme applied to all panels")

        except Exception as e:
            logger.error("Failed to apply theme to panels: %s", str(e))

    def _update_components_from_settings(self) -> None:
        """Update components based on current settings."""
        try:
            # Update all panels with new settings
            if hasattr(self, "work_panel"):
                self.work_panel.update_settings()

            if hasattr(self, "result_panel"):
                self.result_panel.update_settings()

            if hasattr(self, "log_panel"):
                self.log_panel.update_settings()

            # Update log level if changed
            log_level = self.config_manager.get("application.logging_config.log_level", "INFO")
            # TODO: Update logging configuration

            # Update other settings as needed
            logger.info("All components updated from settings")

        except Exception as e:
            logger.error("Failed to update components from settings: %s", str(e))

    def _change_theme(self) -> None:
        """Handle change theme action."""
        self.log_panel.add_log("테마 변경됨")

    def _toggle_fullscreen(self) -> None:
        """Handle toggle fullscreen action."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _toggle_panels(self) -> None:
        """Handle toggle panels action."""
        self.log_panel.add_log("패널 토글됨")

    def _scan_files(self) -> None:
        """Handle scan files action."""
        if hasattr(self, "file_processing_vm"):
            # Get scan directories from work panel or use default
            scan_dirs = getattr(self.work_panel, "get_scan_directories", lambda: [])()
            if not scan_dirs:
                # Use a default directory or show dialog
                from PyQt5.QtWidgets import QFileDialog

                scan_dirs = QFileDialog.getExistingDirectory(self, "스캔할 디렉토리 선택")
                if scan_dirs:
                    scan_dirs = [scan_dirs]

            if scan_dirs:
                self.file_processing_vm.execute_command("scan_files", scan_dirs)
                self.log_panel.add_log("파일 스캔 시작됨")
            else:
                self.log_panel.add_log("스캔할 디렉토리가 선택되지 않았습니다")
        else:
            self.work_panel.scan_files()
            self.log_panel.add_log("파일 스캔 시작됨")

    def _organize_files(self) -> None:
        """Handle organize files action."""
        if hasattr(self, "file_processing_vm"):
            # Check if we have file groups to organize
            groups = self.file_processing_vm.get_property("file_groups", [])
            if groups:
                self.file_processing_vm.execute_command("organize_files")
                self.log_panel.add_log("파일 정리 시작됨")
            else:
                self.log_panel.add_log("정리할 파일 그룹이 없습니다")
        else:
            self.work_panel.organize_files()
            self.log_panel.add_log("파일 정리 시작됨")

    def _preview_organization(self) -> None:
        """Handle preview organization action."""
        if hasattr(self, "file_processing_vm"):
            # Get current file groups and show preview
            groups = self.file_processing_vm.get_property("file_groups", [])
            if groups:
                self.log_panel.add_log(f"미리보기: {len(groups)}개 그룹 준비됨")
                # Here you could show a preview dialog
            else:
                self.log_panel.add_log("미리보기할 그룹이 없습니다")
        else:
            self.work_panel.preview_organization()
            self.log_panel.add_log("미리보기 생성됨")

    def _show_help(self) -> None:
        """Handle show help action."""
        self.log_panel.add_log("도움말 열림")

    def _show_about(self) -> None:
        """Handle show about action."""
        self.log_panel.add_log("정보 대화상자 열림")

    def cleanup(self) -> None:
        """Clean up resources when the window is closed."""
        logger.info("Cleaning up MainWindow resources")

        # Clean up ViewModels
        for name, viewmodel in self._viewmodels.items():
            logger.debug(f"Cleaning up ViewModel: {name}")
            viewmodel.cleanup()

        self._viewmodels.clear()

        # Clean up panels
        if hasattr(self, "log_panel"):
            self.log_panel.cleanup()

        if hasattr(self, "result_panel"):
            self.result_panel.cleanup()

        logger.info("MainWindow cleanup completed")

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        logger.info("MainWindow close event triggered")
        self.cleanup()
        super().closeEvent(event)
