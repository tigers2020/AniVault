"""Log panel for displaying application logs."""

from datetime import datetime

from PyQt5.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ..themes import DarkTheme


class LogPanel(QGroupBox):
    """Panel for displaying application execution logs."""

    def __init__(self, parent=None) -> None:
        """Initialize the log panel."""
        super().__init__("실행 로그", parent)
        self.theme = DarkTheme()
        self._setup_ui()
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
        clear_btn.setStyleSheet(self.theme.get_button_style("danger"))
        clear_btn.clicked.connect(self.clear_logs)

        auto_scroll_label = QLabel("자동 스크롤")
        auto_scroll_label.setStyleSheet("color: #94a3b8; font-size: 12px;")

        controls_layout.addWidget(clear_btn)
        controls_layout.addStretch()
        controls_layout.addWidget(auto_scroll_label)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        self.log_text.setStyleSheet(self.theme.get_text_edit_style())

        # Auto-scroll to bottom
        self.log_text.verticalScrollBar().rangeChanged.connect(
            lambda: self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )
        )

        layout.addLayout(controls_layout)
        layout.addWidget(self.log_text)

    def _add_sample_logs(self) -> None:
        """Add sample log entries."""
        sample_logs = [
            "[12:30:01] 프로그램 시작",
            "[12:30:05] 소스 폴더 스캔 완료 (120개 항목)",
            "[12:30:15] 그룹화 작업 완료 (15개 그룹)",
            "[12:30:20] TMDB API 연결 성공",
            "[12:30:25] 메타데이터 검색 완료",
            "[12:30:30] 정리 작업 준비 완료",
        ]

        for log_entry in sample_logs:
            self.add_log(log_entry, show_timestamp=False)

    def add_log(self, message: str, log_type: str = "INFO", show_timestamp: bool = True) -> None:
        """Add a log entry to the log panel."""
        if show_timestamp:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {message}"
        else:
            log_entry = message

        # Color code based on log type
        if log_type == "ERROR":
            color = "#ef4444"
        elif log_type == "WARNING":
            color = "#f59e0b"
        elif log_type == "SUCCESS":
            color = "#10b981"
        else:  # INFO
            color = "#94a3b8"

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
        return self.log_text.document().blockCount()
