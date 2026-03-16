"""Group Card Widget for GUI v2."""

from __future__ import annotations

from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class GroupCard(QPushButton):
    """Group card widget displaying group information."""

    # Signals
    card_clicked = Signal(int)  # Emitted when card is clicked, emits group ID

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize group card widget."""
        super().__init__(parent)
        self._group_data: dict | None = None
        self._group_id: int | None = None
        self._setup_ui()

        # Connect QPushButton's clicked signal to emit our custom signal
        super().clicked.connect(self._on_clicked)

    def _on_clicked(self) -> None:
        """Handle button click and emit card_clicked signal."""
        if self._group_id is not None:
            self.card_clicked.emit(self._group_id)

    def _setup_ui(self) -> None:
        """Set up the group card UI."""
        self.setObjectName("groupCard")
        self.setCheckable(False)

        # Set size policy to ensure proper sizing
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        # Set minimum size to ensure card is visible
        self.setMinimumSize(QSize(300, 200))

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("groupCardHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 20, 20, 20)

        self.title_label = QLabel()
        self.title_label.setObjectName("groupTitle")
        header_layout.addWidget(self.title_label)

        meta_layout = QHBoxLayout()
        self.meta_label = QLabel()
        self.meta_label.setObjectName("groupMeta")
        meta_layout.addWidget(self.meta_label)
        meta_layout.addStretch()

        header_layout.addLayout(meta_layout)

        layout.addWidget(header)

        # Body
        body = QWidget()
        body.setObjectName("groupCardBody")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(20, 20, 20, 20)
        body_layout.setSpacing(16)

        # Info badges
        self.info_widget = QWidget()
        info_layout = QHBoxLayout(self.info_widget)
        info_layout.setSpacing(8)
        info_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.addWidget(self.info_widget)

        # Progress section (for matched groups)
        self.progress_widget = QWidget()
        progress_layout = QVBoxLayout(self.progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(4)

        progress_label_layout = QHBoxLayout()
        progress_label_layout.setContentsMargins(0, 0, 0, 0)

        self.progress_label = QLabel("매칭 신뢰도")
        self.progress_label.setObjectName("progressLabel")
        progress_label_layout.addWidget(self.progress_label)
        progress_label_layout.addStretch()

        self.progress_value = QLabel()
        self.progress_value.setObjectName("progressValue")
        progress_label_layout.addWidget(self.progress_value)

        progress_layout.addLayout(progress_label_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("groupConfidenceBar")
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setTextVisible(False)

        progress_layout.addWidget(self.progress_bar)

        body_layout.addWidget(self.progress_widget)

        # Unmatched message
        self.unmatched_label = QLabel("TMDB 매칭을 실행하세요.")
        self.unmatched_label.setObjectName("unmatchedMessage")

        body_layout.addWidget(self.unmatched_label)

        layout.addWidget(body)

    def set_group_data(self, group_data: dict) -> None:
        """Set group data to display.

        Args:
            group_data: Dictionary with group information:
                - id: int
                - title: str
                - season: int
                - episodes: int
                - files: int
                - matched: bool
                - confidence: int (0-100, optional)
                - resolution: str
                - language: str
        """
        self._group_data = group_data
        self._group_id = group_data.get("id")

        # Set title
        title_text = group_data.get("title", "")
        self.title_label.setText(title_text)

        # Set meta (season, episodes)
        season = group_data.get("season", 0)
        episodes = group_data.get("episodes", 0)
        self.meta_label.setText(f"시즌 {season} | 총 {episodes}화")

        # Clear info badges
        while self.info_widget.layout().count():
            child = self.info_widget.layout().takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Add info badges
        files = group_data.get("files", 0)
        resolution = group_data.get("resolution", "")
        language = group_data.get("language", "").upper()

        files_badge = QLabel(f"{files}개 파일")
        files_badge.setObjectName("infoBadge")
        self.info_widget.layout().addWidget(files_badge)

        res_badge = QLabel(resolution)
        res_badge.setObjectName("infoBadge")
        self.info_widget.layout().addWidget(res_badge)

        lang_badge = QLabel(language)
        lang_badge.setObjectName("infoBadge")
        self.info_widget.layout().addWidget(lang_badge)

        # Match status
        matched = group_data.get("matched", False)
        if matched:
            match_badge = QLabel("✓ 매칭됨")
            match_badge.setObjectName("infoBadge")
            match_badge.setProperty("matched", True)  # noqa: FBT003
            self.info_widget.layout().addWidget(match_badge)

            # Show progress
            self.progress_widget.show()
            self.unmatched_label.hide()

            confidence = group_data.get("confidence", 0)
            self.progress_value.setText(f"{confidence}%")
            self.progress_bar.setValue(confidence)
        else:
            match_badge = QLabel("미매칭")
            match_badge.setObjectName("infoBadge")
            match_badge.setProperty("unmatched", True)  # noqa: FBT003
            self.info_widget.layout().addWidget(match_badge)

            # Hide progress, show unmatched message
            self.progress_widget.hide()
            self.unmatched_label.show()
