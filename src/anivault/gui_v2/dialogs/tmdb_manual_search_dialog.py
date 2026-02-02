"""TMDB manual search dialog for GUI v2.

Allows user to search TMDB and manually select a match for a group.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from anivault.shared.models.api.tmdb import TMDBSearchResult
from anivault.shared.models.metadata import FileMetadata

logger = logging.getLogger(__name__)


class TmdbSearchWorker(QThread):
    """Worker thread for TMDB search."""

    finished = Signal(list)  # list[TMDBSearchResult]
    error = Signal(str)

    def __init__(self, tmdb_client: object, query: str) -> None:
        super().__init__()
        self._tmdb_client = tmdb_client
        self._query = query.strip()

    def run(self) -> None:
        """Run async TMDB search in thread."""
        if not self._query:
            self.finished.emit([])
            return

        try:
            response = asyncio.run(self._tmdb_client.search_media(self._query))
            self.finished.emit(response.results if response else [])
        except Exception as exc:  # noqa: BLE001
            logger.exception("TMDB search failed for '%s'", self._query)
            self.error.emit(str(exc))


class TmdbManualSearchDialog(QDialog):
    """Dialog for manual TMDB search and selection."""

    def __init__(
        self,
        group_title: str,
        file_metadata_list: list[FileMetadata],
        tmdb_client: object,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize dialog.

        Args:
            group_title: Default search query (group title).
            file_metadata_list: Files to update when user selects a match.
            tmdb_client: TMDB API client for search.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._group_title = group_title
        self._file_metadata_list = file_metadata_list
        self._tmdb_client = tmdb_client
        self._results: list[TMDBSearchResult] = []
        self._selected_result: TMDBSearchResult | None = None
        self._worker: TmdbSearchWorker | None = None

        self.setWindowTitle("TMDB 수동 검색")
        self.setMinimumSize(500, 400)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up dialog UI."""
        layout = QVBoxLayout(self)

        # Search section
        search_layout = QHBoxLayout()
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("검색어 입력 (예: 진격의 거인)")
        self._search_edit.setText(self._group_title)
        self._search_edit.returnPressed.connect(self._on_search_clicked)
        search_layout.addWidget(self._search_edit)

        self._search_btn = QPushButton("검색")
        self._search_btn.setObjectName("btnPrimary")
        self._search_btn.clicked.connect(self._on_search_clicked)
        search_layout.addWidget(self._search_btn)
        layout.addLayout(search_layout)

        # Results section
        results_label = QLabel("검색 결과")
        results_label.setObjectName("dialogSectionTitle")
        layout.addWidget(results_label)

        self._results_list = QListWidget()
        self._results_list.setAlternatingRowColors(True)
        self._results_list.itemSelectionChanged.connect(self._on_selection_changed)
        self._results_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._results_list)

        # Status
        self._status_label = QLabel("검색어를 입력하고 검색 버튼을 누르세요.")
        self._status_label.setObjectName("dialogSubtitle")
        layout.addWidget(self._status_label)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)

        self._ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_button.setText("선택")
        self._ok_button.setEnabled(False)
        layout.addWidget(button_box)

    def _on_search_clicked(self) -> None:
        """Handle search button click."""
        query = self._search_edit.text().strip()
        if not query:
            self._status_label.setText("검색어를 입력해주세요.")
            return

        self._search_btn.setEnabled(False)
        self._status_label.setText("검색 중...")
        self._results_list.clear()
        self._results = []

        self._worker = TmdbSearchWorker(self._tmdb_client, query)
        self._worker.finished.connect(self._on_search_finished)
        self._worker.error.connect(self._on_search_error)
        self._worker.start()

    def _on_search_finished(self, results: list[TMDBSearchResult]) -> None:
        """Handle search completion."""
        self._search_btn.setEnabled(True)
        self._results = results

        if not results:
            self._status_label.setText("검색 결과가 없습니다. 다른 검색어로 시도해보세요.")
            return

        self._status_label.setText(f"{len(results)}개 결과를 찾았습니다. 항목을 선택하세요.")
        for result in results:
            date_str = result.display_date[:4] if result.display_date else "?"
            media_type = "TV" if result.media_type == "tv" else "영화"
            title = result.display_title
            item_text = f"{title} ({date_str}) - {media_type}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, result)
            self._results_list.addItem(item)

    def _on_search_error(self, error_msg: str) -> None:
        """Handle search error."""
        self._search_btn.setEnabled(True)
        self._status_label.setText("검색 중 오류가 발생했습니다.")
        QMessageBox.warning(
            self,
            "TMDB 검색 오류",
            f"검색에 실패했습니다.\n\n{error_msg}\n\nTMDB API 키가 설정되어 있는지 확인해주세요.",
        )

    def _on_selection_changed(self) -> None:
        """Handle result selection change."""
        current = self._results_list.currentItem()
        self._ok_button.setEnabled(current is not None)

    def _on_item_double_clicked(self) -> None:
        """Handle double-click on result (same as accept)."""
        if self._ok_button.isEnabled():
            self._on_accept()

    def _on_accept(self) -> None:
        """Handle OK/Select button - apply selected match."""
        current = self._results_list.currentItem()
        if not current:
            return

        result = current.data(Qt.ItemDataRole.UserRole)
        if not isinstance(result, TMDBSearchResult):
            return

        self._selected_result = result
        self.accept()

    def get_updated_metadata(self) -> list[FileMetadata] | None:
        """Return updated FileMetadata list if user selected a match.

        Returns:
            Updated list of FileMetadata with TMDB match applied, or None if cancelled.
        """
        if not self._selected_result:
            return None

        result = self._selected_result
        year = None
        if result.display_date and len(result.display_date) >= 4:
            try:
                year = int(result.display_date[:4])
            except ValueError:
                pass

        updated: list[FileMetadata] = []
        for fm in self._file_metadata_list:
            updated.append(
                replace(
                    fm,
                    tmdb_id=result.id,
                    title=result.display_title,
                    media_type=result.media_type,
                    year=year or fm.year,
                    match_confidence=1.0,  # User explicitly selected, full confidence
                )
            )
        return updated
