"""Settings Dialog for GUI v2."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from anivault.config import Settings, update_and_save_config
from anivault.config.auto_scanner import AutoScanner
from anivault.config.settings_provider import get_settings_provider
from anivault.shared.constants import FolderDefaults

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Settings dialog with tabs for API key and folders."""

    def __init__(self, app_context, parent: QWidget | None = None) -> None:
        """Initialize settings dialog.

        Args:
            app_context: Application context containing settings and config path.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.setModal(True)
        self.resize(900, 600)
        self.app_context = app_context
        self.config_path = app_context.config_path
        self.auto_scanner = AutoScanner(self.config_path)
        self._setup_ui()
        self._load_current_config()

    def _setup_ui(self) -> None:
        """Set up the settings dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("dialogHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 20, 20, 20)

        title_layout = QHBoxLayout()
        title_label = QLabel("설정")
        title_label.setObjectName("dialogTitle")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        close_btn = QPushButton("닫기")
        close_btn.setObjectName("btnGhost")
        close_btn.clicked.connect(self.accept)
        title_layout.addWidget(close_btn)

        header_layout.addLayout(title_layout)

        subtitle = QLabel("TMDB API 키 및 폴더 설정")
        subtitle.setObjectName("dialogSubtitle")
        header_layout.addWidget(subtitle)

        layout.addWidget(header)

        # Tabs
        tabs = QTabWidget()
        tabs.setObjectName("settingsTabs")

        # API Key tab
        api_tab = self._create_api_tab()
        tabs.addTab(api_tab, "API Key")

        # Folders tab
        folders_tab = self._create_folders_tab()
        tabs.addTab(folders_tab, "Folders")

        layout.addWidget(tabs)

        # Actions
        actions = QWidget()
        actions.setObjectName("dialogActions")
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(20, 20, 20, 20)
        actions_layout.setSpacing(10)
        actions_layout.addStretch()

        reset_btn = QPushButton("초기화")
        reset_btn.setObjectName("btnGhost")
        reset_btn.clicked.connect(self._on_reset)
        actions_layout.addWidget(reset_btn)

        save_btn = QPushButton("저장")
        save_btn.setObjectName("btnPrimary")
        save_btn.clicked.connect(self._on_save)
        actions_layout.addWidget(save_btn)

        layout.addWidget(actions)

    def _create_api_tab(self) -> QWidget:
        """Create API Key tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # API Key field
        api_key_field = QVBoxLayout()
        api_key_label = QLabel("TMDB API Key")
        api_key_label.setObjectName("fieldLabel")
        api_key_field.addWidget(api_key_label)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Enter your TMDB API key")
        api_key_field.addWidget(self.api_key_input)

        help_text = QLabel('Get your API key from: <a href="https://www.themoviedb.org/settings/api">https://www.themoviedb.org/settings/api</a>')
        help_text.setOpenExternalLinks(True)
        help_text.setObjectName("helpText")
        api_key_field.addWidget(help_text)

        layout.addLayout(api_key_field)

        # Note section
        note_widget = QWidget()
        note_widget.setObjectName("noteWidget")
        note_layout = QVBoxLayout(note_widget)
        note_layout.setContentsMargins(16, 16, 16, 16)

        note_title = QLabel("💡 참고")
        note_title.setObjectName("noteTitle")
        note_layout.addWidget(note_title)

        note_text = QLabel("API 키는 .env 파일에 안전하게 저장됩니다. (config.toml에는 저장되지 않음)")
        note_text.setObjectName("noteText")
        note_layout.addWidget(note_text)

        layout.addWidget(note_widget)

        layout.addStretch()

        return tab

    def _create_folders_tab(self) -> QWidget:
        """Create Folders tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        # Source folder
        source_field = QVBoxLayout()
        source_label = QLabel("Source Folder")
        source_label.setObjectName("fieldLabel")
        source_field.addWidget(source_label)

        source_input_layout = QHBoxLayout()
        self.source_folder_input = QLineEdit()
        self.source_folder_input.setPlaceholderText("Select source folder for media files")
        source_input_layout.addWidget(self.source_folder_input)

        browse_source_btn = QPushButton("Browse...")
        browse_source_btn.setObjectName("btnGhost")
        browse_source_btn.clicked.connect(lambda: self._browse_folder(self.source_folder_input))
        source_input_layout.addWidget(browse_source_btn)

        source_field.addLayout(source_input_layout)

        source_help = QLabel("미디어 파일이 있는 소스 폴더")
        source_help.setObjectName("helpText")
        source_field.addWidget(source_help)

        layout.addLayout(source_field)

        # Target folder
        target_field = QVBoxLayout()
        target_label = QLabel("Target Folder")
        target_label.setObjectName("fieldLabel")
        target_field.addWidget(target_label)

        target_input_layout = QHBoxLayout()
        self.target_folder_input = QLineEdit()
        self.target_folder_input.setPlaceholderText("Select target folder for organized files")
        target_input_layout.addWidget(self.target_folder_input)

        browse_target_btn = QPushButton("Browse...")
        browse_target_btn.setObjectName("btnGhost")
        browse_target_btn.clicked.connect(lambda: self._browse_folder(self.target_folder_input))
        target_input_layout.addWidget(browse_target_btn)

        target_field.addLayout(target_input_layout)

        target_help = QLabel("정리된 파일을 저장할 대상 폴더")
        target_help.setObjectName("helpText")
        target_field.addWidget(target_help)

        layout.addLayout(target_field)

        # Organization path template
        options_widget = QWidget()
        options_widget.setObjectName("optionsWidget")
        options_layout = QVBoxLayout(options_widget)
        options_layout.setContentsMargins(16, 16, 16, 16)
        options_layout.setSpacing(12)

        options_title = QLabel("정리 경로 템플릿")
        options_title.setObjectName("optionsTitle")
        options_layout.addWidget(options_title)

        self.organize_path_template = QLineEdit()
        self.organize_path_template.setPlaceholderText("{해상도}/{연도}/{제목}/{시즌}")
        self.organize_path_template.setText(FolderDefaults.ORGANIZE_PATH_TEMPLATE)
        options_layout.addWidget(self.organize_path_template)

        hint_label = QLabel(
            "사용 가능한 플레이스홀더: {해상도}, {연도}, {제목}, {시즌}\n예: {해상도}/{연도}/{제목}/{시즌} → 1080p/2013/진격의 거인/Season 01"
        )
        hint_label.setObjectName("helpText")
        hint_label.setWordWrap(True)
        options_layout.addWidget(hint_label)

        layout.addWidget(options_widget)

        # Auto scan settings
        auto_scan_widget = QWidget()
        auto_scan_widget.setObjectName("autoScanWidget")
        auto_scan_layout = QVBoxLayout(auto_scan_widget)
        auto_scan_layout.setContentsMargins(16, 16, 16, 16)
        auto_scan_layout.setSpacing(16)

        auto_scan_title = QLabel("자동 스캔 설정")
        auto_scan_title.setObjectName("autoScanTitle")
        auto_scan_layout.addWidget(auto_scan_title)

        self.auto_scan_startup = QCheckBox("시작 시 소스 폴더 자동 스캔")
        auto_scan_layout.addWidget(self.auto_scan_startup)

        scan_interval_layout = QHBoxLayout()
        interval_label = QLabel("스캔 간격 (분)")
        interval_label.setObjectName("fieldLabel")
        scan_interval_layout.addWidget(interval_label)

        self.scan_interval = QSpinBox()
        self.scan_interval.setRange(0, 1440)
        self.scan_interval.setValue(0)
        scan_interval_layout.addWidget(self.scan_interval)
        scan_interval_layout.addStretch()

        auto_scan_layout.addLayout(scan_interval_layout)

        interval_help = QLabel("0 = 비활성화")
        interval_help.setObjectName("helpText")
        auto_scan_layout.addWidget(interval_help)

        self.include_subdirs = QCheckBox("하위 디렉터리 포함")
        self.include_subdirs.setChecked(True)
        auto_scan_layout.addWidget(self.include_subdirs)

        layout.addWidget(auto_scan_widget)

        layout.addStretch()

        return tab

    def _browse_folder(self, line_edit: QLineEdit) -> None:
        """Browse for folder and set in line edit."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            line_edit.setText(folder)

    def _on_reset(self) -> None:
        """Handle reset button click."""
        self.api_key_input.clear()
        self.source_folder_input.clear()
        self.target_folder_input.clear()
        self.organize_path_template.setText(FolderDefaults.ORGANIZE_PATH_TEMPLATE)
        self.auto_scan_startup.setChecked(False)
        self.scan_interval.setValue(0)
        self.include_subdirs.setChecked(True)

    def _load_current_config(self) -> None:
        """Load current configuration into the dialog."""
        try:
            settings = self.app_context.settings

            # Load API key from environment (not from config for security)
            api_key = os.environ.get("TMDB_API_KEY", "")
            if api_key:
                self.api_key_input.setText(api_key)

            # Load folder settings
            if settings.folders:
                self.source_folder_input.setText(settings.folders.source_folder or "")
                self.target_folder_input.setText(settings.folders.target_folder or "")
                template = settings.folders.organize_path_template or FolderDefaults.ORGANIZE_PATH_TEMPLATE
                self.organize_path_template.setText(template)
                self.auto_scan_startup.setChecked(settings.folders.auto_scan_on_startup or False)
                self.scan_interval.setValue(settings.folders.auto_scan_interval_minutes or 0)
                self.include_subdirs.setChecked(
                    settings.folders.include_subdirectories if settings.folders.include_subdirectories is not None else True
                )
        except Exception:
            logger.exception("Failed to load current configuration")
            # Continue with empty form

    def _on_save(self) -> None:
        """Handle save button click."""
        api_key = self.api_key_input.text().strip()

        # Validate API key if provided
        if api_key and len(api_key) < 10:
            QMessageBox.warning(
                self,
                "Invalid API Key",
                "API 키는 최소 10자 이상이어야 합니다.",
            )
            return

        try:
            # Save API key to .env file if provided
            if api_key:
                self._save_api_key_to_env_file(api_key)

                # Update memory cache
                def update_api_key(cfg: Settings) -> None:
                    cfg.api.tmdb.api_key = api_key

                update_and_save_config(update_api_key, self.config_path)

            # Save folder settings
            self._save_folder_settings()

            # Reload in-memory settings so rest of app (scan/organize/status bar) uses new values
            self.app_context.settings = get_settings_provider().get_settings(self.config_path)

            # Refresh main window status bar so new source folder is displayed
            parent = self.parent()
            if parent is not None and hasattr(parent, "_refresh_status_bar"):
                parent._refresh_status_bar()

            # Show success message
            QMessageBox.information(
                self,
                "설정 저장됨",
                "설정이 성공적으로 저장되었습니다.\n\n🔒 보안 알림: API 키는 .env 파일에 안전하게 저장되었습니다.\n(config.toml에는 저장되지 않음)",
            )

            # Close dialog
            self.accept()

        except Exception as e:
            logger.exception("Failed to save settings")
            QMessageBox.critical(
                self,
                "저장 실패",
                f"설정 저장 중 오류가 발생했습니다:\n{e!s}",
            )

    def _save_api_key_to_env_file(self, api_key: str) -> None:
        """Save API key to .env file.

        Args:
            api_key: The API key to save
        """
        env_file = Path(".env")
        env_lines = []

        # Read existing .env file if it exists
        if env_file.exists():
            with open(env_file, encoding="utf-8") as f:
                env_lines = f.readlines()

        # Update or add TMDB_API_KEY
        found = False
        for i, line in enumerate(env_lines):
            if line.startswith("TMDB_API_KEY="):
                env_lines[i] = f"TMDB_API_KEY={api_key}\n"
                found = True
                break

        if not found:
            env_lines.append(f"TMDB_API_KEY={api_key}\n")

        # Write back to .env file
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(env_lines)

        # Set environment variable for current process
        os.environ["TMDB_API_KEY"] = api_key

        logger.info("API key saved to .env file")

    def _save_folder_settings(self) -> None:
        """Save folder settings to configuration."""
        source_folder = self.source_folder_input.text().strip()
        target_folder = self.target_folder_input.text().strip()
        path_template = self.organize_path_template.text().strip() or FolderDefaults.ORGANIZE_PATH_TEMPLATE
        auto_scan_startup = self.auto_scan_startup.isChecked()
        auto_scan_interval = self.scan_interval.value()
        include_subdirs = self.include_subdirs.isChecked()

        # Update folder settings using auto scanner
        success, error = self.auto_scanner.update_folder_settings(
            source_folder=source_folder,
            target_folder=target_folder,
            organize_path_template=path_template,
            auto_scan_on_startup=auto_scan_startup,
            auto_scan_interval_minutes=auto_scan_interval,
            include_subdirectories=include_subdirs,
        )

        if not success:
            message = f"Failed to update folder settings: {error}"
            raise ValueError(message)

        logger.info("Folder settings saved successfully")
