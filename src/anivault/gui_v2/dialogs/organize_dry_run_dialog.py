"""Dry-run preview dialog for organize execution in GUI v2."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from anivault.core.models import FileOperation

logger = logging.getLogger(__name__)


class OrganizeDryRunDialog(QDialog):
    """Dialog to preview organize plan before execution."""

    def __init__(self, plan: list[Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._plan = plan
        self._confirmed = False
        self.setWindowTitle("파일 정리 미리보기")
        self.setMinimumSize(900, 600)
        self._setup_ui()

    def is_confirmed(self) -> bool:
        """Return True if the user confirmed execution."""
        return self._confirmed

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        header_layout = QHBoxLayout()

        title_label = QLabel("📦 정리 계획 미리보기")
        title_label.setObjectName("dialogTitle")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        count_label = QLabel(f"총 {len(self._plan)}개 작업")
        count_label.setObjectName("dialogSubtitle")
        header_layout.addWidget(count_label)
        layout.addLayout(header_layout)

        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["파일명", "현재 위치", "이동 위치"])
        table.setRowCount(len(self._plan))
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        for row, operation in enumerate(self._plan):
            source_path, destination_path = _extract_paths(operation)

            name_item = QTableWidgetItem(source_path.name if source_path else "Unknown")
            name_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            table.setItem(row, 0, name_item)

            source_text = str(source_path.parent) if source_path else "Unknown"
            source_item = QTableWidgetItem(source_text)
            source_item.setToolTip(source_text)
            table.setItem(row, 1, source_item)

            dest_text = str(destination_path) if destination_path else "Unknown"
            dest_item = QTableWidgetItem(dest_text)
            dest_item.setToolTip(dest_text)
            table.setItem(row, 2, dest_item)

        table.setColumnWidth(0, 280)
        table.setColumnWidth(1, 300)
        layout.addWidget(table)

        button_box = QDialogButtonBox()
        confirm_button = button_box.addButton("확인", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_button = button_box.addButton("취소", QDialogButtonBox.ButtonRole.RejectRole)
        confirm_button.clicked.connect(self._on_confirm)
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(button_box)

    def _on_confirm(self) -> None:
        self._confirmed = True
        self.accept()


def _extract_paths(operation: Any) -> tuple[Path | None, Path | None]:
    if isinstance(operation, FileOperation):
        return operation.source_path, operation.destination_path
    if isinstance(operation, dict):
        source = operation.get("source") or operation.get("source_path")
        destination = operation.get("destination") or operation.get("destination_path")
        return _to_path(source), _to_path(destination)
    return None, None


def _to_path(value: Any) -> Path | None:
    if isinstance(value, Path):
        return value
    if isinstance(value, str):
        return Path(value)
    return None
