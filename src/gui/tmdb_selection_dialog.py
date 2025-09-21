"""TMDB 검색 결과 선택 다이얼로그

TMDB 검색 결과가 없거나 여러 개일 때 사용자가 수동으로 선택할 수 있는 다이얼로그입니다.
"""

import logging
from typing import Any

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ..core.tmdb_client import TMDBClient, TMDBConfig, TMDBError
from ..themes.theme_manager import ThemeManager

logger = logging.getLogger(__name__)


class TMDBSelectionDialog(QDialog):
    """TMDB 검색 결과 선택 다이얼로그"""

    # 선택된 결과를 반환하는 시그널
    result_selected = pyqtSignal(dict)  # 선택된 TMDB 결과

    def __init__(
        self,
        parent=None,
        theme_manager: ThemeManager | None = None,
        api_key: str | None = None,
    ):
        super().__init__(parent)
        self.theme_manager = theme_manager or ThemeManager()
        self.api_key = api_key
        self.tmdb_client: TMDBClient | None = None
        self.search_results: list[dict[str, Any]] = []
        self.selected_result: dict[str, Any] | None = None

        self.setWindowTitle("TMDB 검색 결과 선택")
        self.setModal(True)
        self.resize(800, 600)

        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 검색 섹션
        search_group = self._create_search_section()
        layout.addWidget(search_group)

        # 결과 섹션
        results_group = self._create_results_section()
        layout.addWidget(results_group)

        # 버튼 섹션
        buttons_layout = self._create_buttons_section()
        layout.addLayout(buttons_layout)

    def _create_search_section(self) -> QGroupBox:
        """검색 섹션 생성"""
        group = QGroupBox("검색")

        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 검색어 입력
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("검색어:"))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("애니메이션 제목을 입력하세요...")
        self.search_input.returnPressed.connect(self._perform_search)
        search_layout.addWidget(self.search_input)

        self.search_btn = QPushButton("검색")
        self.search_btn.clicked.connect(self._perform_search)
        search_layout.addWidget(self.search_btn)

        layout.addLayout(search_layout)

        # 검색 상태 라벨
        self.status_label = QLabel("검색어를 입력하고 검색 버튼을 클릭하세요.")
        self.status_label.label_type = "secondary"
        layout.addWidget(self.status_label)

        # ThemeManager를 통해 스타일 적용
        self.theme_manager.apply_theme(group)

        return group

    def _create_results_section(self) -> QGroupBox:
        """결과 섹션 생성"""
        group = QGroupBox("검색 결과")

        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 결과 테이블
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["포스터", "제목", "원제", "첫 방영일"])

        # 테이블 설정
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.results_table.setAlternatingRowColors(True)
        
        # 선택 가능하도록 설정
        self.results_table.setFocusPolicy(Qt.StrongFocus)
        self.results_table.setTabKeyNavigation(True)

        # 컬럼 너비 설정
        header = self.results_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 포스터
            header.setSectionResizeMode(1, QHeaderView.Stretch)  # 제목
            header.setSectionResizeMode(2, QHeaderView.Stretch)  # 원제
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 첫 방영일

        # 더블클릭으로 선택
        self.results_table.itemDoubleClicked.connect(self._on_result_double_clicked)
        self.results_table.itemSelectionChanged.connect(self._on_selection_changed)

        layout.addWidget(self.results_table)

        # ThemeManager를 통해 스타일 적용
        self.theme_manager.apply_theme(group)

        return group

    def _create_buttons_section(self) -> QHBoxLayout:
        """버튼 섹션 생성"""
        layout = QHBoxLayout()
        layout.addStretch()

        # 선택 버튼
        self.select_btn = QPushButton("선택")
        self.select_btn.clicked.connect(self._on_select_clicked)
        self.select_btn.setEnabled(False)
        layout.addWidget(self.select_btn)

        # 취소 버튼
        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.cancel_btn)

        # ThemeManager를 통해 버튼 스타일 적용
        self.theme_manager.apply_theme(self.select_btn)
        self.theme_manager.apply_theme(self.cancel_btn)

        return layout

    def _apply_theme(self):
        """테마 적용"""
        # ThemeManager를 통해 테마 적용
        self.theme_manager.apply_theme(self)

    def set_initial_search(self, query: str, results: list[dict[str, Any]] | None = None):
        """초기 검색어와 결과 설정"""
        logger.info(f"Setting initial search: query='{query}', results_count={len(results) if results else 0}")
        
        self.search_input.setText(query)
        if results:
            logger.info(f"Displaying {len(results)} pre-loaded results")
            self._display_results(results)
        else:
            logger.info("No pre-loaded results, performing new search")
            self._perform_search()

    def _perform_search(self):
        """TMDB 검색 수행"""
        query = self.search_input.text().strip()
        if not query:
            self.status_label.setText("검색어를 입력해주세요.")
            return

        self.status_label.setText("검색 중...")
        self.search_btn.setEnabled(False)

        try:
            # TMDB 클라이언트 초기화 (지연 초기화)
            if not self.tmdb_client:
                if not self.api_key:
                    self.status_label.setText("TMDB API 키가 설정되지 않았습니다.")
                    return
                config = TMDBConfig(api_key=self.api_key)
                self.tmdb_client = TMDBClient(config)

            # TMDB Multi Search 수행
            # At this point, tmdb_client is guaranteed to be initialized

            search_results, needs_selection = self.tmdb_client.search_comprehensive(
                query, language="ko-KR"
            )

            # Initialize results list
            results = []

            if search_results:
                # Convert SearchResult objects to dict format for display
                for search_result in search_results:
                    result_dict = {
                        "id": search_result.id,
                        "name": search_result.title,
                        "original_name": search_result.original_title,
                        "first_air_date": search_result.year,
                        "overview": search_result.overview,
                        "poster_path": search_result.poster_path,
                        "vote_average": search_result.vote_average,
                        "vote_count": search_result.vote_count,
                        "popularity": search_result.popularity,
                        "media_type": search_result.media_type,
                        "quality_score": search_result.quality_score,
                    }
                    results.append(result_dict)

            # 단일 결과이고 선택이 필요하지 않은 경우 자동 선택
            if not needs_selection and len(results) == 1:
                logger.info(f"Single result found, auto-selecting: {results[0]['name']}")
                self._select_result(results[0])
                return

            self._display_results(results)

            if not results:
                self.status_label.setText(f"'{query}'에 대한 검색 결과가 없습니다.")
            else:
                self.status_label.setText(f"'{query}' 검색 결과: {len(results)}개")

        except TMDBError as e:
            logger.error(f"TMDB search failed: {e}")
            self.status_label.setText(f"검색 실패: {e!s}")
            QMessageBox.warning(self, "검색 오류", f"TMDB 검색 중 오류가 발생했습니다:\n{e!s}")
        except Exception as e:
            logger.error(f"Unexpected error during TMDB search: {e}")
            self.status_label.setText("검색 중 오류가 발생했습니다.")
            QMessageBox.critical(self, "오류", f"예상치 못한 오류가 발생했습니다:\n{e!s}")
        finally:
            self.search_btn.setEnabled(True)

    def _display_results(self, results: list[dict[str, Any]]):
        """검색 결과를 테이블에 표시"""
        # 결과를 인스턴스 변수에 저장
        self.search_results = results
        self.results_table.setRowCount(len(results))

        for i, result in enumerate(results):
            # 포스터 (이미지 URL만 표시, 실제 이미지는 나중에 로드)
            poster_item = QTableWidgetItem("📷")
            poster_item.setData(Qt.UserRole, result.get("poster_path"))
            poster_item.setFlags(poster_item.flags() | Qt.ItemIsSelectable)
            self.results_table.setItem(i, 0, poster_item)

            # 제목
            title = result.get("name", "제목 없음")
            title_item = QTableWidgetItem(title)
            title_item.setFlags(title_item.flags() | Qt.ItemIsSelectable)
            self.results_table.setItem(i, 1, title_item)

            # 원제
            original_title = result.get("original_name", title)
            original_item = QTableWidgetItem(original_title)
            original_item.setFlags(original_item.flags() | Qt.ItemIsSelectable)
            self.results_table.setItem(i, 2, original_item)

            # 첫 방영일
            first_air_date = result.get("first_air_date", "알 수 없음")
            date_item = QTableWidgetItem(first_air_date)
            date_item.setFlags(date_item.flags() | Qt.ItemIsSelectable)
            self.results_table.setItem(i, 3, date_item)

        # 첫 번째 결과 선택
        if results:
            self.results_table.selectRow(0)
            # 선택 상태 업데이트
            self._on_selection_changed()

    def _on_result_double_clicked(self, item: QTableWidgetItem):
        """결과 더블클릭 시 선택"""
        logger.debug(f"Double-clicked on item at row {item.row()}")
        self._on_select_clicked()

    def _on_selection_changed(self):
        """선택 변경 시"""
        current_row = self.results_table.currentRow()
        has_selection = current_row >= 0 and current_row < len(self.search_results)
        self.select_btn.setEnabled(has_selection)
        
        # 디버깅을 위한 로그
        logger.debug(f"Selection changed: row={current_row}, has_selection={has_selection}, total_results={len(self.search_results)}")

    def _select_result(self, result: dict):
        """결과를 자동으로 선택"""
        self.selected_result = result
        self.result_selected.emit(self.selected_result)
        self.accept()

    def _on_select_clicked(self):
        """선택 버튼 클릭 시"""
        current_row = self.results_table.currentRow()
        logger.debug(f"Select button clicked: current_row={current_row}, total_results={len(self.search_results)}")
        
        if current_row >= 0 and current_row < len(self.search_results):
            self.selected_result = self.search_results[current_row]
            logger.info(f"Selected result: {self.selected_result.get('name', 'Unknown')}")
            self.result_selected.emit(self.selected_result)
            self.accept()
        else:
            logger.warning(f"Invalid selection: row={current_row}, total_results={len(self.search_results)}")
            QMessageBox.warning(self, "선택 오류", "유효한 항목을 선택해주세요.")

    def get_selected_result(self) -> dict[str, Any] | None:
        """선택된 결과 반환"""
        return self.selected_result
