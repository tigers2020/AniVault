"""
Organize Progress Dialog

This module provides a dialog for showing file organization progress
with real-time status updates and cancellation support.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class OrganizeProgressDialog(QDialog):
    """Dialog showing file organization progress."""

    def __init__(self, total_files: int, parent: QWidget | None = None) -> None:
        """Initialize organize progress dialog.

        Args:
            total_files: Total number of files to organize
            parent: Parent widget
        """
        super().__init__(parent)
        self.total_files = total_files
        self.organized_files = 0
        self.failed_files = 0

        self.setWindowTitle("파일 정리 진행 중")
        self.setMinimumSize(600, 400)
        self.setModal(True)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Title
        title_label = QLabel("📦 파일 정리 중...")
        title_label.setObjectName("dialogTitle")
        layout.addWidget(title_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel(f"0 / {self.total_files} 파일 정리됨")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)

        # Log area
        log_header = QLabel("📝 작업 로그:")
        log_header.setObjectName("logHeader")
        layout.addWidget(log_header)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setObjectName("logOutput")
        layout.addWidget(self.log_text)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Cancel button
        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.setObjectName("cancelButton")
        self.cancel_btn.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def update_progress(self, progress: int, current_file: str = "") -> None:
        """Update progress bar and current file status.

        Args:
            progress: Progress percentage (0-100)
            current_file: Name of the file currently being processed
        """
        self.progress_bar.setValue(progress)

        # Update status label with current file
        if current_file:
            self.status_label.setText(
                f"{self.organized_files + self.failed_files} / {self.total_files} " f"파일 정리 중... (현재: {current_file})",
            )
        else:
            self.status_label.setText(
                f"{self.organized_files + self.failed_files} / {self.total_files} " f"파일 정리됨",
            )

    def add_file_result(self, result: dict[str, str]) -> None:
        """Add file organization result to log.

        Args:
            result: Dictionary with source, destination, status, and optional error
        """
        source = Path(result.get("source", "")).name
        destination = result.get("destination", "")
        success = result.get("success", "False")

        # Debug logging
        logger.debug(
            "File result: success=%s, source=%s, destination=%s",
            success,
            source,
            destination,
        )

        if success in ("True", "true", "1", "yes"):  # Handle various success indicators
            self.organized_files += 1
            log_entry = f"✅ {source} → {destination}"
            self.log_text.append(log_entry)
        else:
            self.failed_files += 1
            error = result.get("error", "Unknown error")
            log_entry = f"❌ {source}: {error}"
            self.log_text.append(log_entry)

        # Update status label
        self.status_label.setText(
            f"{self.organized_files} / {self.total_files} 파일 정리됨 " f"(실패: {self.failed_files})",
        )

        # Scroll to bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum(),
        )

    def show_completion(self, organized_count: int, total_count: int) -> None:
        """Show completion message.

        Args:
            organized_count: Number of successfully organized files
            total_count: Total number of files
        """
        self.progress_bar.setValue(100)

        if organized_count == total_count:
            message = f"✅ 완료! {organized_count}개 파일 정리 성공"
            self.log_text.append(f"\n{message}")
            self.log_text.append("🗑️ 빈 폴더 정리 중...")
        else:
            failed_count = total_count - organized_count
            message = f"⚠️ 완료! {organized_count}개 성공, {failed_count}개 실패"
            self.log_text.append(f"\n{message}")

        self.status_label.setText(message)

        # Change cancel button to close
        self.cancel_btn.setText("닫기")
        self.cancel_btn.setObjectName("closeButton")

        # Scroll to bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum(),
        )

    def show_error(self, error_msg: str) -> None:
        """Show error message.

        Args:
            error_msg: Error message to display
        """
        self.log_text.append(f"\n❌ 오류: {error_msg}")
        self.cancel_btn.setText("닫기")

        # Scroll to bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum(),
        )

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        if self.cancel_btn.text() == "닫기":
            self.accept()
        else:
            self.reject()
