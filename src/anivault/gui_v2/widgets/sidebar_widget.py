"""Sidebar Widget for GUI v2."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class SidebarWidget(QWidget):
    """Sidebar widget with navigation menu and statistics."""

    # Signals
    view_changed = Signal(str)  # Emits view name when navigation item clicked

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize sidebar widget."""
        super().__init__(parent)
        self._current_view = "groups"
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the sidebar UI."""
        self.setObjectName("sidebar")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(32)

        # Navigation sections
        self._add_navigation_section(layout, "작업", [
            ("groups", "📊 그룹 관리"),
            ("tmdb", "🎬 TMDB 매칭"),
            ("organize", "📦 파일 정리"),
            ("rollback", "↩️ 롤백 관리"),
        ])

        self._add_navigation_section(layout, "도구", [
            ("verify", "✅ 검증"),
            ("cache", "💾 캐시 관리"),
            ("logs", "📝 로그 보기"),
        ])

        # Statistics card
        self._add_statistics_card(layout)

        layout.addStretch()

    def _add_navigation_section(
        self, parent_layout: QVBoxLayout, title: str, items: list[tuple[str, str]]
    ) -> None:
        """Add a navigation section to the sidebar."""
        # Section title
        title_label = QLabel(title)
        title_label.setObjectName("sidebarTitle")
        parent_layout.addWidget(title_label)

        # Navigation items
        for view_name, label in items:
            item_btn = QPushButton(label)
            item_btn.setObjectName("sidebarItem")
            item_btn.setCheckable(True)
            if view_name == self._current_view:
                item_btn.setChecked(True)
                item_btn.setProperty("active", True)

            item_btn.clicked.connect(
                lambda checked, vn=view_name: self._on_view_clicked(vn)
            )
            parent_layout.addWidget(item_btn)

    def _add_statistics_card(self, parent_layout: QVBoxLayout) -> None:
        """Add statistics card to sidebar."""
        stats_widget = QWidget()
        stats_widget.setObjectName("statsCard")
        stats_layout = QVBoxLayout(stats_widget)
        stats_layout.setContentsMargins(16, 16, 16, 16)
        stats_layout.setSpacing(8)

        # Title
        title_label = QLabel("통계")
        title_label.setObjectName("sidebarTitle")
        stats_layout.addWidget(title_label)

        # Statistics
        self._add_stat_item(stats_layout, "총 그룹", "totalGroups", "0")
        self._add_stat_item(stats_layout, "총 파일", "totalFiles", "0")
        self._add_stat_item(stats_layout, "매칭 완료", "matchedGroups", "0")
        self._add_stat_item(stats_layout, "정리 대기", "pendingOrganize", "0")

        parent_layout.addWidget(stats_widget)

    def _add_stat_item(
        self, layout: QVBoxLayout, label_text: str, value_object_name: str, initial_value: str
    ) -> None:
        """Add a statistics item."""
        item_layout = QHBoxLayout()
        item_layout.setContentsMargins(0, 8, 0, 8)

        label = QLabel(label_text)
        label.setObjectName("statLabel")
        item_layout.addWidget(label)

        item_layout.addStretch()

        value = QLabel(initial_value)
        value.setObjectName("statValue")
        value.setProperty("id", value_object_name)
        item_layout.addWidget(value)

        layout.addLayout(item_layout)

    def _on_view_clicked(self, view_name: str) -> None:
        """Handle navigation item click."""
        self._current_view = view_name

        # Map view names to button labels
        view_labels = {
            "groups": "📊 그룹 관리",
            "tmdb": "🎬 TMDB 매칭",
            "organize": "📦 파일 정리",
            "rollback": "↩️ 롤백 관리",
            "verify": "✅ 검증",
            "cache": "💾 캐시 관리",
            "logs": "📝 로그 보기",
        }

        # Update active state for all items
        target_label = view_labels.get(view_name, "")
        for child in self.findChildren(QPushButton, "sidebarItem"):
            is_active = child.text() == target_label
            child.setProperty("active", is_active)
            child.setChecked(is_active)
            child.style().unpolish(child)
            child.style().polish(child)

        self.view_changed.emit(view_name)

    def update_statistic(self, stat_id: str, value: str) -> None:
        """Update a statistics value."""
        # Find label with matching property id
        for label in self.findChildren(QLabel):
            if label.property("id") == stat_id:
                label.setText(value)
                break
