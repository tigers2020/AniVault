"""Settings dialog for AniVault application."""

import logging

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Settings dialog for configuring application preferences."""

    # Signal emitted when settings are saved
    settings_saved = pyqtSignal()

    def __init__(self, parent: QWidget | None = None, config_manager: ConfigManager | None = None):
        """Initialize the settings dialog.

        Args:
            parent: Parent widget
            config_manager: Configuration manager instance
        """
        super().__init__(parent)
        self.config_manager = config_manager or ConfigManager()

        self.setWindowTitle("설정")
        self.setModal(True)
        self.resize(600, 500)

        # Initialize UI
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create tabs
        self._create_general_tab()
        self._create_file_organization_tab()
        self._create_api_tab()
        self._create_theme_tab()
        self._create_advanced_tab()

        # Create button box
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults
        )
        self.button_box.accepted.connect(self._save_settings)
        self.button_box.rejected.connect(self.reject)
        restore_button = self.button_box.button(QDialogButtonBox.RestoreDefaults)
        if restore_button:
            restore_button.clicked.connect(self._restore_defaults)

        layout.addWidget(self.button_box)

    def _create_general_tab(self) -> None:
        """Create the general settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # GUI State Group
        gui_group = QGroupBox("GUI 상태")
        gui_layout = QFormLayout(gui_group)

        self.remember_last_session = QCheckBox("마지막 세션 기억하기")
        gui_layout.addRow(self.remember_last_session)

        self.last_source_dir = QLineEdit()
        self.last_source_dir.setReadOnly(True)
        self.source_dir_button = QPushButton("찾아보기...")
        self.source_dir_button.clicked.connect(self._browse_source_directory)

        source_layout = QHBoxLayout()
        source_layout.addWidget(self.last_source_dir)
        source_layout.addWidget(self.source_dir_button)
        gui_layout.addRow("마지막 소스 디렉토리:", source_layout)

        self.last_destination_dir = QLineEdit()
        self.last_destination_dir.setReadOnly(True)
        self.destination_dir_button = QPushButton("찾아보기...")
        self.destination_dir_button.clicked.connect(self._browse_destination_directory)

        dest_layout = QHBoxLayout()
        dest_layout.addWidget(self.last_destination_dir)
        dest_layout.addWidget(self.destination_dir_button)
        gui_layout.addRow("마지막 대상 디렉토리:", dest_layout)

        layout.addWidget(gui_group)

        # Accessibility Group
        accessibility_group = QGroupBox("접근성")
        accessibility_layout = QFormLayout(accessibility_group)

        self.high_contrast_mode = QCheckBox("고대비 모드")
        accessibility_layout.addRow(self.high_contrast_mode)

        self.keyboard_navigation = QCheckBox("키보드 탐색")
        accessibility_layout.addRow(self.keyboard_navigation)

        self.screen_reader_support = QCheckBox("스크린 리더 지원")
        accessibility_layout.addRow(self.screen_reader_support)

        layout.addWidget(accessibility_group)

        # Logging Group
        logging_group = QGroupBox("로깅")
        logging_layout = QFormLayout(logging_group)

        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        logging_layout.addRow("로그 레벨:", self.log_level)

        self.log_to_file = QCheckBox("파일에 로그 저장")
        logging_layout.addRow(self.log_to_file)

        layout.addWidget(logging_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "일반")

    def _create_file_organization_tab(self) -> None:
        """Create the file organization settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # File Organization Group
        file_group = QGroupBox("파일 정리")
        file_layout = QFormLayout(file_group)

        self.destination_root = QLineEdit()
        self.destination_root.setReadOnly(True)
        self.dest_root_button = QPushButton("찾아보기...")
        self.dest_root_button.clicked.connect(self._browse_destination_root)

        dest_root_layout = QHBoxLayout()
        dest_root_layout.addWidget(self.destination_root)
        dest_root_layout.addWidget(self.dest_root_button)
        file_layout.addRow("대상 루트 디렉토리:", dest_root_layout)

        self.organize_mode = QComboBox()
        self.organize_mode.addItems(["복사", "이동", "하드링크", "심볼릭링크"])
        file_layout.addRow("정리 모드:", self.organize_mode)

        self.naming_scheme = QComboBox()
        self.naming_scheme.addItems(["standard", "anime", "tv_show", "movie"])
        file_layout.addRow("명명 규칙:", self.naming_scheme)

        self.safe_mode = QCheckBox("안전 모드")
        file_layout.addRow(self.safe_mode)

        self.backup_before_organize = QCheckBox("정리 전 백업")
        file_layout.addRow(self.backup_before_organize)

        self.prefer_anitopy = QCheckBox("Anitopy 우선 사용")
        file_layout.addRow(self.prefer_anitopy)

        self.fallback_parser = QComboBox()
        self.fallback_parser.addItems(["FileParser", "AnitopyParser", "ManualParser"])
        file_layout.addRow("폴백 파서:", self.fallback_parser)

        self.realtime_monitoring = QCheckBox("실시간 모니터링")
        file_layout.addRow(self.realtime_monitoring)

        self.auto_refresh_interval = QSpinBox()
        self.auto_refresh_interval.setRange(1, 3600)
        self.auto_refresh_interval.setSuffix(" 초")
        file_layout.addRow("자동 새로고침 간격:", self.auto_refresh_interval)

        self.show_advanced_options = QCheckBox("고급 옵션 표시")
        file_layout.addRow(self.show_advanced_options)

        layout.addWidget(file_group)

        # Backup Settings Group
        backup_group = QGroupBox("백업 설정")
        backup_layout = QFormLayout(backup_group)

        self.backup_location = QLineEdit()
        self.backup_location.setReadOnly(True)
        self.backup_button = QPushButton("찾아보기...")
        self.backup_button.clicked.connect(self._browse_backup_location)

        backup_path_layout = QHBoxLayout()
        backup_path_layout.addWidget(self.backup_location)
        backup_path_layout.addWidget(self.backup_button)
        backup_layout.addRow("백업 위치:", backup_path_layout)

        self.max_backup_count = QSpinBox()
        self.max_backup_count.setRange(1, 1000)
        backup_layout.addRow("최대 백업 수:", self.max_backup_count)

        layout.addWidget(backup_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "파일 정리")

    def _create_api_tab(self) -> None:
        """Create the API settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # TMDB API Group
        tmdb_group = QGroupBox("TMDB API")
        tmdb_layout = QFormLayout(tmdb_group)

        self.tmdb_api_key = QLineEdit()
        self.tmdb_api_key.setEchoMode(QLineEdit.Password)
        self.tmdb_api_key.setPlaceholderText("TMDB API 키를 입력하세요")
        tmdb_layout.addRow("API 키:", self.tmdb_api_key)

        self.tmdb_language = QComboBox()
        self.tmdb_language.addItems(["ko-KR", "en-US", "ja-JP", "zh-CN"])
        tmdb_layout.addRow("언어:", self.tmdb_language)

        # API Key visibility toggle
        self.show_api_key = QCheckBox("API 키 표시")
        self.show_api_key.toggled.connect(self._toggle_api_key_visibility)
        tmdb_layout.addRow(self.show_api_key)

        layout.addWidget(tmdb_group)

        # API Status
        status_group = QGroupBox("API 상태")
        status_layout = QVBoxLayout(status_group)

        self.api_status_label = QLabel("상태: 확인되지 않음")
        status_layout.addWidget(self.api_status_label)

        self.test_api_button = QPushButton("API 연결 테스트")
        self.test_api_button.clicked.connect(self._test_api_connection)
        status_layout.addWidget(self.test_api_button)

        layout.addWidget(status_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "API")

    def _create_theme_tab(self) -> None:
        """Create the theme settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Theme Group
        theme_group = QGroupBox("테마")
        theme_layout = QFormLayout(theme_group)

        self.theme = QComboBox()
        self.theme.addItems(["auto", "light", "dark"])
        theme_layout.addRow("테마:", self.theme)

        self.language = QComboBox()
        self.language.addItems(["ko", "en", "ja", "zh"])
        theme_layout.addRow("언어:", self.language)

        layout.addWidget(theme_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "테마")

    def _create_advanced_tab(self) -> None:
        """Create the advanced settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Performance Group
        performance_group = QGroupBox("성능")
        performance_layout = QFormLayout(performance_group)

        self.max_workers = QSpinBox()
        self.max_workers.setRange(1, 32)
        self.max_workers.setValue(4)
        performance_layout.addRow("최대 워커 수:", self.max_workers)

        self.cache_size = QSpinBox()
        self.cache_size.setRange(10, 10000)
        self.cache_size.setValue(1000)
        self.cache_size.setSuffix(" MB")
        performance_layout.addRow("캐시 크기:", self.cache_size)

        layout.addWidget(performance_group)

        # Debug Group
        debug_group = QGroupBox("디버그")
        debug_layout = QFormLayout(debug_group)

        self.debug_mode = QCheckBox("디버그 모드")
        debug_layout.addRow(self.debug_mode)

        self.verbose_logging = QCheckBox("상세 로깅")
        debug_layout.addRow(self.verbose_logging)

        layout.addWidget(debug_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "고급")

    def _load_settings(self) -> None:
        """Load settings from configuration manager."""
        try:
            # General settings
            self.remember_last_session.setChecked(
                self.config_manager.get("user_preferences.gui_state.remember_last_session", True)
            )
            self.last_source_dir.setText(
                self.config_manager.get("user_preferences.gui_state.last_source_directory", "")
            )
            self.last_destination_dir.setText(
                self.config_manager.get("user_preferences.gui_state.last_destination_directory", "")
            )

            # Accessibility
            self.high_contrast_mode.setChecked(
                self.config_manager.get("user_preferences.accessibility.high_contrast_mode", False)
            )
            self.keyboard_navigation.setChecked(
                self.config_manager.get("user_preferences.accessibility.keyboard_navigation", True)
            )
            self.screen_reader_support.setChecked(
                self.config_manager.get(
                    "user_preferences.accessibility.screen_reader_support", True
                )
            )

            # Logging
            log_level = self.config_manager.get("application.logging_config.log_level", "INFO")
            self.log_level.setCurrentText(log_level)
            self.log_to_file.setChecked(
                self.config_manager.get("application.logging_config.log_to_file", False)
            )

            # File organization
            self.destination_root.setText(
                self.config_manager.get("application.file_organization.destination_root", "")
            )
            organize_mode = self.config_manager.get(
                "application.file_organization.organize_mode", "복사"
            )
            self.organize_mode.setCurrentText(organize_mode)

            naming_scheme = self.config_manager.get(
                "application.file_organization.naming_scheme", "standard"
            )
            self.naming_scheme.setCurrentText(naming_scheme)

            self.safe_mode.setChecked(
                self.config_manager.get("application.file_organization.safe_mode", True)
            )
            self.backup_before_organize.setChecked(
                self.config_manager.get(
                    "application.file_organization.backup_before_organize", False
                )
            )
            self.prefer_anitopy.setChecked(
                self.config_manager.get("application.file_organization.prefer_anitopy", False)
            )

            fallback_parser = self.config_manager.get(
                "application.file_organization.fallback_parser", "FileParser"
            )
            self.fallback_parser.setCurrentText(fallback_parser)

            self.realtime_monitoring.setChecked(
                self.config_manager.get("application.file_organization.realtime_monitoring", False)
            )
            self.auto_refresh_interval.setValue(
                self.config_manager.get("application.file_organization.auto_refresh_interval", 30)
            )
            self.show_advanced_options.setChecked(
                self.config_manager.get(
                    "application.file_organization.show_advanced_options", False
                )
            )

            # Backup settings
            self.backup_location.setText(
                self.config_manager.get("application.backup_settings.backup_location", "")
            )
            self.max_backup_count.setValue(
                self.config_manager.get("application.backup_settings.max_backup_count", 10)
            )

            # API settings
            self.tmdb_api_key.setText(self.config_manager.get_tmdb_api_key() or "")
            tmdb_language = self.config_manager.get_tmdb_language()
            self.tmdb_language.setCurrentText(tmdb_language)

            # Theme settings
            theme = self.config_manager.get_theme()
            self.theme.setCurrentText(theme)
            language = self.config_manager.get_language()
            self.language.setCurrentText(language)

            logger.info("Settings loaded successfully")

        except Exception as e:
            logger.error("Failed to load settings: %s", str(e))

    def _save_settings(self) -> None:
        """Save settings to configuration manager."""
        try:
            # General settings
            self.config_manager.set(
                "user_preferences.gui_state.remember_last_session",
                self.remember_last_session.isChecked(),
            )
            self.config_manager.set(
                "user_preferences.gui_state.last_source_directory", self.last_source_dir.text()
            )
            self.config_manager.set(
                "user_preferences.gui_state.last_destination_directory",
                self.last_destination_dir.text(),
            )

            # Accessibility
            self.config_manager.set(
                "user_preferences.accessibility.high_contrast_mode",
                self.high_contrast_mode.isChecked(),
            )
            self.config_manager.set(
                "user_preferences.accessibility.keyboard_navigation",
                self.keyboard_navigation.isChecked(),
            )
            self.config_manager.set(
                "user_preferences.accessibility.screen_reader_support",
                self.screen_reader_support.isChecked(),
            )

            # Logging
            self.config_manager.set(
                "application.logging_config.log_level", self.log_level.currentText()
            )
            self.config_manager.set(
                "application.logging_config.log_to_file", self.log_to_file.isChecked()
            )

            # File organization
            self.config_manager.set(
                "application.file_organization.destination_root", self.destination_root.text()
            )
            self.config_manager.set(
                "application.file_organization.organize_mode", self.organize_mode.currentText()
            )
            self.config_manager.set(
                "application.file_organization.naming_scheme", self.naming_scheme.currentText()
            )
            self.config_manager.set(
                "application.file_organization.safe_mode", self.safe_mode.isChecked()
            )
            self.config_manager.set(
                "application.file_organization.backup_before_organize",
                self.backup_before_organize.isChecked(),
            )
            self.config_manager.set(
                "application.file_organization.prefer_anitopy", self.prefer_anitopy.isChecked()
            )
            self.config_manager.set(
                "application.file_organization.fallback_parser", self.fallback_parser.currentText()
            )
            self.config_manager.set(
                "application.file_organization.realtime_monitoring",
                self.realtime_monitoring.isChecked(),
            )
            self.config_manager.set(
                "application.file_organization.auto_refresh_interval",
                self.auto_refresh_interval.value(),
            )
            self.config_manager.set(
                "application.file_organization.show_advanced_options",
                self.show_advanced_options.isChecked(),
            )

            # Backup settings
            self.config_manager.set(
                "application.backup_settings.backup_location", self.backup_location.text()
            )
            self.config_manager.set(
                "application.backup_settings.max_backup_count", self.max_backup_count.value()
            )

            # API settings
            if self.tmdb_api_key.text().strip():
                self.config_manager.set(
                    "services.tmdb_api.api_key", self.tmdb_api_key.text().strip()
                )
            self.config_manager.set("services.tmdb_api.language", self.tmdb_language.currentText())

            # Theme settings
            self.config_manager.set_theme(self.theme.currentText())
            self.config_manager.set_language(self.language.currentText())

            # Save configuration
            if self.config_manager.save_config():
                logger.info("Settings saved successfully")
                self.settings_saved.emit()
                self.accept()
            else:
                logger.error("Failed to save settings")

        except Exception as e:
            logger.error("Failed to save settings: %s", str(e))

    def _restore_defaults(self) -> None:
        """Restore default settings."""
        try:
            # Get default configuration
            default_config = self.config_manager._get_default_config()

            # Reset all fields to default values
            self.remember_last_session.setChecked(
                default_config["user_preferences"]["gui_state"]["remember_last_session"]
            )
            self.last_source_dir.clear()
            self.last_destination_dir.clear()

            self.high_contrast_mode.setChecked(
                default_config["user_preferences"]["accessibility"]["high_contrast_mode"]
            )
            self.keyboard_navigation.setChecked(
                default_config["user_preferences"]["accessibility"]["keyboard_navigation"]
            )
            self.screen_reader_support.setChecked(
                default_config["user_preferences"]["accessibility"]["screen_reader_support"]
            )

            self.log_level.setCurrentText(
                default_config["application"]["logging_config"]["log_level"]
            )
            self.log_to_file.setChecked(
                default_config["application"]["logging_config"]["log_to_file"]
            )

            self.destination_root.clear()
            self.organize_mode.setCurrentText(
                default_config["application"]["file_organization"]["organize_mode"]
            )
            self.naming_scheme.setCurrentText(
                default_config["application"]["file_organization"]["naming_scheme"]
            )
            self.safe_mode.setChecked(
                default_config["application"]["file_organization"]["safe_mode"]
            )
            self.backup_before_organize.setChecked(
                default_config["application"]["file_organization"]["backup_before_organize"]
            )
            self.prefer_anitopy.setChecked(
                default_config["application"]["file_organization"]["prefer_anitopy"]
            )
            self.fallback_parser.setCurrentText(
                default_config["application"]["file_organization"]["fallback_parser"]
            )
            self.realtime_monitoring.setChecked(
                default_config["application"]["file_organization"]["realtime_monitoring"]
            )
            self.auto_refresh_interval.setValue(
                default_config["application"]["file_organization"]["auto_refresh_interval"]
            )
            self.show_advanced_options.setChecked(
                default_config["application"]["file_organization"]["show_advanced_options"]
            )

            self.backup_location.clear()
            self.max_backup_count.setValue(
                default_config["application"]["backup_settings"]["max_backup_count"]
            )

            self.tmdb_api_key.clear()
            self.tmdb_language.setCurrentText("ko-KR")

            self.theme.setCurrentText(
                default_config["user_preferences"]["theme_preferences"]["theme"]
            )
            self.language.setCurrentText(
                default_config["user_preferences"]["theme_preferences"]["language"]
            )

            logger.info("Settings restored to defaults")

        except Exception as e:
            logger.error("Failed to restore default settings: %s", str(e))

    def _browse_source_directory(self) -> None:
        """Browse for source directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "소스 디렉토리 선택", self.last_source_dir.text()
        )
        if directory:
            self.last_source_dir.setText(directory)

    def _browse_destination_directory(self) -> None:
        """Browse for destination directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "대상 디렉토리 선택", self.last_destination_dir.text()
        )
        if directory:
            self.last_destination_dir.setText(directory)

    def _browse_destination_root(self) -> None:
        """Browse for destination root directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "대상 루트 디렉토리 선택", self.destination_root.text()
        )
        if directory:
            self.destination_root.setText(directory)

    def _browse_backup_location(self) -> None:
        """Browse for backup location."""
        directory = QFileDialog.getExistingDirectory(
            self, "백업 위치 선택", self.backup_location.text()
        )
        if directory:
            self.backup_location.setText(directory)

    def _toggle_api_key_visibility(self, checked: bool) -> None:
        """Toggle API key visibility."""
        if checked:
            self.tmdb_api_key.setEchoMode(QLineEdit.Normal)
        else:
            self.tmdb_api_key.setEchoMode(QLineEdit.Password)

    def _test_api_connection(self) -> None:
        """Test API connection."""
        api_key = self.tmdb_api_key.text().strip()
        if not api_key:
            self.api_status_label.setText("상태: API 키가 입력되지 않았습니다")
            return

        # TODO: Implement actual API connection test
        self.api_status_label.setText("상태: 테스트 중...")
        # For now, just show a placeholder message
        self.api_status_label.setText("상태: API 연결 테스트는 구현 예정입니다")
