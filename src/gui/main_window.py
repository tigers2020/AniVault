"""Main window for AnimeSorter application."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..themes.theme_manager import get_theme_manager

from .anime_details_panel import AnimeDetailsPanel
from .anime_groups_panel import AnimeGroupsPanel
from .group_files_panel import GroupFilesPanel
from .log_panel import LogPanel
from .work_panel import WorkPanel


class MainWindow(QMainWindow):
    """Main window for AnimeSorter application."""

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.setWindowTitle("AnimeSorter")
        self.setGeometry(100, 100, 1400, 900)

        # Initialize theme manager
        self.theme_manager = get_theme_manager()

        # Apply theme
        self.theme_manager.apply_theme(self)

        # Create menu bar
        self._create_menu_bar()

        # Create central widget and layout
        self._create_central_widget()

        # Create status bar
        self._create_status_bar()


    def _create_menu_bar(self) -> None:
        """Create the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("파일")
        file_menu.addAction("열기", self._open_files)
        file_menu.addAction("저장", self._save_settings)
        file_menu.addSeparator()
        file_menu.addAction("종료", self.close)

        # Edit menu
        edit_menu = menubar.addMenu("편집")
        edit_menu.addAction("설정", self._open_settings)
        edit_menu.addAction("테마", self._change_theme)

        # View menu
        view_menu = menubar.addMenu("보기")
        view_menu.addAction("전체 화면", self._toggle_fullscreen)
        view_menu.addAction("패널 숨기기", self._toggle_panels)

        # Tools menu
        tools_menu = menubar.addMenu("도구")
        tools_menu.addAction("스캔", self._scan_files)
        tools_menu.addAction("정리", self._organize_files)
        tools_menu.addAction("미리보기", self._preview_organization)

        # Help menu
        help_menu = menubar.addMenu("도움말")
        help_menu.addAction("도움말", self._show_help)
        help_menu.addAction("정보", self._show_about)

    def _create_central_widget(self) -> None:
        """Create the central widget with 4-panel layout."""
        # Create main content widget
        main_content = QWidget()
        main_content.setStyleSheet(f"background-color: {self.theme_manager.get_color('bg_primary')};")
        
        # Main layout
        main_layout = QHBoxLayout(main_content)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Create horizontal splitter for main panels
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setChildrenCollapsible(False)

        # Left panel (Work Panel + Statistics)
        left_panel = self._create_left_panel()
        main_splitter.addWidget(left_panel)

        # Middle panels (Groups + Files)
        middle_panel = self._create_middle_panel()
        main_splitter.addWidget(middle_panel)

        # Right panel (Anime Details)
        right_panel = self._create_right_panel()
        main_splitter.addWidget(right_panel)

        # Set splitter proportions
        main_splitter.setSizes([300, 500, 400])

        # Add splitter to main layout
        main_layout.addWidget(main_splitter)

        # Create vertical layout for main content and log
        content_widget = QWidget()
        content_widget.setStyleSheet(f"background-color: {self.theme_manager.get_color('bg_primary')};")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)
        
        # Add main content
        content_layout.addWidget(main_content)

        # Add log panel at bottom
        self.log_panel = LogPanel()
        content_layout.addWidget(self.log_panel)

        # Set as central widget
        self.setCentralWidget(content_widget)

    def _create_left_panel(self) -> QWidget:
        """Create the left panel with work controls and statistics."""
        panel = QWidget()
        panel.setMaximumWidth(300)
        panel.setMinimumWidth(250)
        panel.setStyleSheet(f"background-color: {self.theme_manager.get_color('bg_primary')};")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Work panel
        self.work_panel = WorkPanel()
        layout.addWidget(self.work_panel)

        # Statistics panel
        stats_group = QGroupBox("통계")
        stats_group.setStyleSheet(self.theme_manager.current_theme.get_group_box_style())

        stats_layout = QGridLayout(stats_group)

        # Statistics cards
        stats_data = [
            ("전체 파일", "120", "primary"),
            ("전체 그룹", "15", "secondary"),
            ("대기 파일", "12", "warning"),
            ("완료 파일", "108", "accent"),
            ("미분류 파일", "5", "error"),
            ("실패 항목", "2", "text_muted"),
        ]

        for i, (label, value, color_name) in enumerate(stats_data):
            row = i // 2
            col = i % 2

            stat_widget = self._create_stat_card(label, value, color_name)
            stats_layout.addWidget(stat_widget, row, col)

        layout.addWidget(stats_group)
        layout.addStretch()

        return panel

    def _create_middle_panel(self) -> QWidget:
        """Create the middle panel with groups and files."""
        panel = QWidget()
        panel.setStyleSheet(f"background-color: {self.theme_manager.get_color('bg_primary')};")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Create vertical splitter for groups and files
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)

        # Anime groups panel
        self.groups_panel = AnimeGroupsPanel()
        splitter.addWidget(self.groups_panel)

        # Group files panel
        self.files_panel = GroupFilesPanel()
        splitter.addWidget(self.files_panel)

        # Set splitter proportions
        splitter.setSizes([300, 200])

        layout.addWidget(splitter)

        return panel

    def _create_right_panel(self) -> QWidget:
        """Create the right panel with anime details."""
        panel = QWidget()
        panel.setMaximumWidth(400)
        panel.setMinimumWidth(300)
        panel.setStyleSheet(f"background-color: {self.theme_manager.get_color('bg_primary')};")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Anime details panel
        self.details_panel = AnimeDetailsPanel()
        layout.addWidget(self.details_panel)

        return panel

    def _create_stat_card(self, label: str, value: str, color_name: str) -> QWidget:
        """Create a statistics card widget."""
        card = QFrame()
        card.frame_type = "card"
        card.setStyleSheet(self.theme_manager.current_theme.get_frame_style("card"))

        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)

        # Value label
        value_label = QLabel(value)
        value_label.label_type = "stat_value"
        value_label.setStyleSheet(
            f"""
            QLabel {{
                font-size: 24px;
                font-weight: bold;
                color: {self.theme_manager.get_color(color_name)};
            }}
        """
        )
        value_label.setAlignment(Qt.AlignCenter)

        # Label
        label_widget = QLabel(label)
        label_widget.label_type = "stat_label"
        label_widget.setStyleSheet(self.theme_manager.current_theme.get_label_style("stat_label"))
        label_widget.setAlignment(Qt.AlignCenter)

        layout.addWidget(value_label)
        layout.addWidget(label_widget)

        return card

    def _create_status_bar(self) -> None:
        """Create the status bar."""
        status_bar = QStatusBar()
        status_bar.showMessage("상태: 준비 완료")
        self.setStatusBar(status_bar)

    # Menu action handlers
    def _open_files(self) -> None:
        """Handle open files action."""
        self.log_panel.add_log("파일 열기 대화상자 열림")

    def _save_settings(self) -> None:
        """Handle save settings action."""
        self.log_panel.add_log("설정 저장됨")

    def _open_settings(self) -> None:
        """Handle open settings action."""
        self.log_panel.add_log("설정 대화상자 열림")

    def _change_theme(self) -> None:
        """Handle change theme action."""
        self.log_panel.add_log("테마 변경됨")

    def _toggle_fullscreen(self) -> None:
        """Handle toggle fullscreen action."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _toggle_panels(self) -> None:
        """Handle toggle panels action."""
        self.log_panel.add_log("패널 토글됨")

    def _scan_files(self) -> None:
        """Handle scan files action."""
        self.work_panel.scan_files()
        self.log_panel.add_log("파일 스캔 시작됨")

    def _organize_files(self) -> None:
        """Handle organize files action."""
        self.work_panel.organize_files()
        self.log_panel.add_log("파일 정리 시작됨")

    def _preview_organization(self) -> None:
        """Handle preview organization action."""
        self.work_panel.preview_organization()
        self.log_panel.add_log("미리보기 생성됨")

    def _show_help(self) -> None:
        """Handle show help action."""
        self.log_panel.add_log("도움말 열림")

    def _show_about(self) -> None:
        """Handle show about action."""
        self.log_panel.add_log("정보 대화상자 열림")
