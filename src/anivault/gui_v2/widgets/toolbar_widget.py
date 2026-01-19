"""Toolbar Widget for GUI v2."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget


class ToolbarWidget(QWidget):
    """Dynamic toolbar widget that changes based on current view."""

    match_clicked = Signal()
    organize_preflight_clicked = Signal()
    organize_execute_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize toolbar widget."""
        super().__init__(parent)
        self._current_view = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the toolbar UI."""
        self.setObjectName("toolbar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 16, 32, 16)
        layout.setSpacing(12)

        self._content_layout = layout

    def set_view(self, view_name: str) -> None:
        """Update toolbar content based on view."""
        self._current_view = view_name

        # Clear existing widgets
        while self._content_layout.count():
            child = self._content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Add view-specific content
        if view_name in ("work", "groups", "tmdb", "organize"):
            self._setup_work_toolbar()
        elif view_name == "subtitles":
            self._setup_subtitles_toolbar()
        else:
            self._setup_default_toolbar()

    def _setup_work_toolbar(self) -> None:
        """Set up unified toolbar for work view."""
        search_box = QLineEdit()
        search_box.setPlaceholderText("그룹, 파일, TMDB 후보 검색...")
        search_box.setObjectName("searchBox")
        self._content_layout.addWidget(search_box)

        filter_all = QPushButton("전체")
        filter_all.setObjectName("btnSecondary")
        self._content_layout.addWidget(filter_all)

        filter_matched = QPushButton("매칭됨")
        filter_matched.setObjectName("btnSecondary")
        self._content_layout.addWidget(filter_matched)

        filter_unmatched = QPushButton("미매칭")
        filter_unmatched.setObjectName("btnSecondary")
        self._content_layout.addWidget(filter_unmatched)

        self._content_layout.addStretch()

        suggest_btn = QPushButton("자동 추천")
        suggest_btn.setObjectName("btnSecondary")
        suggest_btn.clicked.connect(self.match_clicked.emit)
        self._content_layout.addWidget(suggest_btn)

        confirm_btn = QPushButton("확정 매칭")
        confirm_btn.setObjectName("btnSecondary")
        self._content_layout.addWidget(confirm_btn)

        clear_btn = QPushButton("선택 해제")
        clear_btn.setObjectName("btnSecondary")
        self._content_layout.addWidget(clear_btn)

        self._content_layout.addStretch()

        preflight_btn = QPushButton("프리플라이트")
        preflight_btn.setObjectName("btnSecondary")
        preflight_btn.clicked.connect(self.organize_preflight_clicked.emit)
        self._content_layout.addWidget(preflight_btn)

        refresh_btn = QPushButton("새로고침")
        refresh_btn.setObjectName("btnSecondary")
        self._content_layout.addWidget(refresh_btn)

        execute_btn = QPushButton("▶️ 정리 작업 실행")
        execute_btn.setObjectName("btnPrimary")
        execute_btn.clicked.connect(self.organize_execute_clicked.emit)
        self._content_layout.addWidget(execute_btn)

        self._content_layout.addStretch()

        hint = QLabel("현재 탭: <strong>작업</strong>")
        hint.setObjectName("toolbarHint")
        self._content_layout.addWidget(hint)

    def _setup_subtitles_toolbar(self) -> None:
        """Set up toolbar for subtitles-only view."""
        search_box = QLineEdit()
        search_box.setPlaceholderText("자막 파일 검색...")
        search_box.setObjectName("searchBox")
        self._content_layout.addWidget(search_box)

        filter_all = QPushButton("전체")
        filter_all.setObjectName("btnSecondary")
        self._content_layout.addWidget(filter_all)

        filter_matched = QPushButton("매칭됨")
        filter_matched.setObjectName("btnSecondary")
        self._content_layout.addWidget(filter_matched)

        filter_unmatched = QPushButton("미매칭")
        filter_unmatched.setObjectName("btnSecondary")
        self._content_layout.addWidget(filter_unmatched)

        self._content_layout.addStretch()

        suggest_btn = QPushButton("자동 추천")
        suggest_btn.setObjectName("btnSecondary")
        suggest_btn.clicked.connect(self.match_clicked.emit)
        self._content_layout.addWidget(suggest_btn)

        confirm_btn = QPushButton("확정 매칭")
        confirm_btn.setObjectName("btnSecondary")
        self._content_layout.addWidget(confirm_btn)

        clear_btn = QPushButton("선택 해제")
        clear_btn.setObjectName("btnSecondary")
        self._content_layout.addWidget(clear_btn)

        self._content_layout.addStretch()

        preflight_btn = QPushButton("프리플라이트")
        preflight_btn.setObjectName("btnSecondary")
        preflight_btn.clicked.connect(self.organize_preflight_clicked.emit)
        self._content_layout.addWidget(preflight_btn)

        refresh_btn = QPushButton("새로고침")
        refresh_btn.setObjectName("btnSecondary")
        self._content_layout.addWidget(refresh_btn)

        execute_btn = QPushButton("▶️ 정리 작업 실행")
        execute_btn.setObjectName("btnPrimary")
        execute_btn.clicked.connect(self.organize_execute_clicked.emit)
        self._content_layout.addWidget(execute_btn)

        self._content_layout.addStretch()

        hint = QLabel("현재 탭: <strong>자막만</strong>")
        hint.setObjectName("toolbarHint")
        self._content_layout.addWidget(hint)

    def _setup_tmdb_toolbar(self) -> None:
        """Set up toolbar for TMDB view."""
        search_box = QLineEdit()
        search_box.setPlaceholderText("TMDB 후보 검색(샘플)")
        search_box.setObjectName("searchBox")
        self._content_layout.addWidget(search_box)

        suggest_btn = QPushButton("자동 추천")
        suggest_btn.setObjectName("btnSecondary")
        suggest_btn.clicked.connect(self.match_clicked.emit)
        self._content_layout.addWidget(suggest_btn)

        confirm_btn = QPushButton("확정 매칭")
        confirm_btn.setObjectName("btnSecondary")
        self._content_layout.addWidget(confirm_btn)

        clear_btn = QPushButton("선택 해제")
        clear_btn.setObjectName("btnSecondary")
        self._content_layout.addWidget(clear_btn)

        self._content_layout.addStretch()

        hint = QLabel("현재 탭: <strong>TMDB 매칭</strong>")
        hint.setObjectName("toolbarHint")
        self._content_layout.addWidget(hint)

    def _setup_organize_toolbar(self) -> None:
        """Set up toolbar for organize view."""
        search_box = QLineEdit()
        search_box.setPlaceholderText("정리 큐 검색(샘플)")
        search_box.setObjectName("searchBox")
        self._content_layout.addWidget(search_box)

        preflight_btn = QPushButton("프리플라이트")
        preflight_btn.setObjectName("btnSecondary")
        preflight_btn.clicked.connect(self.organize_preflight_clicked.emit)
        self._content_layout.addWidget(preflight_btn)

        refresh_btn = QPushButton("새로고침")
        refresh_btn.setObjectName("btnSecondary")
        self._content_layout.addWidget(refresh_btn)

        execute_btn = QPushButton("▶️ 정리 작업 실행")
        execute_btn.setObjectName("btnPrimary")
        execute_btn.clicked.connect(self.organize_execute_clicked.emit)
        self._content_layout.addWidget(execute_btn)

        self._content_layout.addStretch()

        hint = QLabel("현재 탭: <strong>파일 정리</strong>")
        hint.setObjectName("toolbarHint")
        self._content_layout.addWidget(hint)

    def _setup_default_toolbar(self) -> None:
        """Set up default toolbar."""
        hint = QLabel("현재 탭을 선택하세요")
        hint.setObjectName("toolbarHint")
        self._content_layout.addWidget(hint)
