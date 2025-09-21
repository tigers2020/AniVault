"""Log panel for displaying application logs."""

import logging
from datetime import datetime

from PyQt5.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.config_manager import ConfigManager
from ..themes.theme_manager import get_theme_manager

logger = logging.getLogger(__name__)


class LogPanel(QGroupBox):
    """Panel for displaying application execution logs."""

    def __init__(
        self, parent: QWidget | None = None, config_manager: ConfigManager | None = None
    ) -> None:
        """Initialize the log panel."""
        super().__init__("실행 로그", parent)
        self.theme_manager = get_theme_manager()
        self.config_manager = config_manager or ConfigManager()
        # Apply theme to the GroupBox first
        self.setStyleSheet(self.theme_manager.current_theme.get_group_box_style())
        self._setup_ui()
        self._load_settings()
        self._add_sample_logs()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Log controls
        controls_layout = QHBoxLayout()

        clear_btn = QPushButton("로그 지우기")
        clear_btn.button_type = "danger"
        clear_btn.setStyleSheet(self.theme_manager.current_theme.get_button_style("danger"))
        clear_btn.clicked.connect(self.clear_logs)

        auto_scroll_label = QLabel("자동 스크롤")
        auto_scroll_label.setStyleSheet(
            f"color: {self.theme_manager.get_color('log_info')}; font-size: 12px;"
        )

        controls_layout.addWidget(clear_btn)
        controls_layout.addStretch()
        controls_layout.addWidget(auto_scroll_label)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        self.log_text.setStyleSheet(self.theme_manager.current_theme.get_text_edit_style())

        # Auto-scroll to bottom
        scroll_bar = self.log_text.verticalScrollBar()
        if scroll_bar:
            scroll_bar.rangeChanged.connect(lambda: scroll_bar.setValue(scroll_bar.maximum()))

        layout.addLayout(controls_layout)
        layout.addWidget(self.log_text)

    def _load_settings(self) -> None:
        """Load settings from configuration manager."""
        try:
            # Load log level and file settings
            log_level = self.config_manager.get("application.logging_config.log_level", "INFO")
            log_to_file = self.config_manager.get("application.logging_config.log_to_file", False)

            # Store settings for use in add_log method
            self._log_level = log_level
            self._log_to_file = log_to_file

            # Update log text height based on settings
            if log_to_file:
                self.log_text.setMaximumHeight(100)  # Smaller if logging to file
            else:
                self.log_text.setMaximumHeight(120)  # Default size

            logger.info("LogPanel settings loaded successfully")

        except Exception as e:
            logger.error("Failed to load LogPanel settings: %s", str(e))

    def update_settings(self) -> None:
        """Update panel based on current settings."""
        try:
            self._load_settings()
            logger.info("LogPanel settings updated")
        except Exception as e:
            logger.error("Failed to update LogPanel settings: %s", str(e))

    def _add_sample_logs(self) -> None:
        """Add sample log entries."""
        sample_logs = [
            ("프로그램 시작", "INFO"),
            ("소스 폴더 스캔 완료 (120개 항목)", "SUCCESS"),
            ("일부 파일을 처리할 수 없습니다", "WARNING"),
            ("그룹화 작업 완료 (15개 그룹)", "SUCCESS"),
            ("TMDB API 연결 실패", "ERROR"),
            ("TMDB API 연결 성공", "SUCCESS"),
            ("메타데이터 검색 완료", "INFO"),
            ("정리 작업 준비 완료", "SUCCESS"),
        ]

        for message, log_type in sample_logs:
            self.add_log(message, log_type, show_timestamp=False)

    def add_log(self, message: str, log_type: str = "INFO", show_timestamp: bool = True) -> None:
        """Add a log entry to the log panel."""
        if show_timestamp:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {message}"
        else:
            log_entry = message

        # Get color from theme manager
        color = self.theme_manager.current_theme.get_log_level_color(log_type)

        # Add colored log entry
        self.log_text.append(f'<span style="color: {color};">{log_entry}</span>')

        # Ensure the log text area is visible
        self.log_text.ensureCursorVisible()

    def add_error_log(self, message: str) -> None:
        """Add an error log entry."""
        self.add_log(message, "ERROR")

    def add_warning_log(self, message: str) -> None:
        """Add a warning log entry."""
        self.add_log(message, "WARNING")

    def add_success_log(self, message: str) -> None:
        """Add a success log entry."""
        self.add_log(message, "SUCCESS")

    def clear_logs(self) -> None:
        """Clear all log entries."""
        self.log_text.clear()
        self.add_log("로그가 지워졌습니다", "INFO")

    def get_log_count(self) -> int:
        """Get the number of log entries."""
        document = self.log_text.document()
        if document:
            return int(document.blockCount())
        return 0

    def cleanup(self) -> None:
        """Clean up resources when the panel is destroyed."""
        # Clear log text
        self.log_text.clear()
