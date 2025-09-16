"""Group files panel for displaying files in selected group."""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ..themes import DarkTheme


class GroupFilesPanel(QGroupBox):
    """Panel displaying files in the selected anime group."""

    file_selected = pyqtSignal(str)  # Emits file path when selected

    def __init__(self, parent=None) -> None:
        """Initialize the group files panel."""
        super().__init__("선택된 그룹 파일", parent)
        self.theme = DarkTheme()
        self._setup_ui()
        self._populate_sample_data()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Create table widget
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(3)
        self.files_table.setHorizontalHeaderLabels(["파일명", "해상도", "길이"])

        # Configure table appearance
        self.files_table.setStyleSheet(self.theme.get_table_style())

        # Configure table behavior
        self.files_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.files_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.files_table.setAlternatingRowColors(True)
        self.files_table.setSortingEnabled(True)

        # Set column widths
        header = self.files_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # File name
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Resolution
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Duration

        # Connect selection signal
        self.files_table.itemSelectionChanged.connect(self._on_selection_changed)

        layout.addWidget(self.files_table)

    def _populate_sample_data(self) -> None:
        """Populate the table with sample data."""
        sample_files = [
            ("Ep01_1080p.mkv", "1080p", "24:00"),
            ("Ep02_1080p.mkv", "1080p", "24:00"),
            ("Ep03_1080p.mkv", "1080p", "24:00"),
            ("Ep04_1080p.mkv", "1080p", "24:00"),
            ("Ep05_1080p.mkv", "1080p", "24:00"),
            ("Ep06_1080p.mkv", "1080p", "24:00"),
            ("Ep07_1080p.mkv", "1080p", "24:00"),
            ("Ep08_1080p.mkv", "1080p", "24:00"),
            ("Ep09_1080p.mkv", "1080p", "24:00"),
            ("Ep10_1080p.mkv", "1080p", "24:00"),
            ("Ep11_1080p.mkv", "1080p", "24:00"),
            ("Ep12_1080p.mkv", "1080p", "24:00"),
        ]

        self.files_table.setRowCount(len(sample_files))

        for row, (file_name, resolution, duration) in enumerate(sample_files):
            # File name
            name_item = QTableWidgetItem(file_name)
            name_item.setData(Qt.UserRole, file_name)  # Store file name for selection
            self.files_table.setItem(row, 0, name_item)

            # Resolution
            res_item = QTableWidgetItem(resolution)
            res_item.setTextAlignment(Qt.AlignCenter)
            self.files_table.setItem(row, 1, res_item)

            # Duration
            dur_item = QTableWidgetItem(duration)
            dur_item.setTextAlignment(Qt.AlignCenter)
            self.files_table.setItem(row, 2, dur_item)

    def _on_selection_changed(self) -> None:
        """Handle selection change in the files table."""
        current_row = self.files_table.currentRow()
        if current_row >= 0:
            file_name_item = self.files_table.item(current_row, 0)
            if file_name_item:
                file_name = file_name_item.data(Qt.UserRole)
                self.file_selected.emit(file_name)

    def get_selected_file(self) -> str:
        """Get the currently selected file name."""
        current_row = self.files_table.currentRow()
        if current_row >= 0:
            file_name_item = self.files_table.item(current_row, 0)
            if file_name_item:
                return file_name_item.data(Qt.UserRole)
        return ""

    def load_group_files(self, group_name: str, files: list) -> None:
        """Load files for a specific group."""
        self.files_table.setRowCount(0)

        for file_info in files:
            row_count = self.files_table.rowCount()
            self.files_table.insertRow(row_count)

            # File name
            name_item = QTableWidgetItem(file_info.get("name", ""))
            name_item.setData(Qt.UserRole, file_info.get("path", ""))
            self.files_table.setItem(row_count, 0, name_item)

            # Resolution
            res_item = QTableWidgetItem(file_info.get("resolution", ""))
            res_item.setTextAlignment(Qt.AlignCenter)
            self.files_table.setItem(row_count, 1, res_item)

            # Duration
            dur_item = QTableWidgetItem(file_info.get("duration", ""))
            dur_item.setTextAlignment(Qt.AlignCenter)
            self.files_table.setItem(row_count, 2, dur_item)

    def add_file(self, file_name: str, resolution: str, duration: str) -> None:
        """Add a new file to the table."""
        row_count = self.files_table.rowCount()
        self.files_table.insertRow(row_count)

        # File name
        name_item = QTableWidgetItem(file_name)
        name_item.setData(Qt.UserRole, file_name)
        self.files_table.setItem(row_count, 0, name_item)

        # Resolution
        res_item = QTableWidgetItem(resolution)
        res_item.setTextAlignment(Qt.AlignCenter)
        self.files_table.setItem(row_count, 1, res_item)

        # Duration
        dur_item = QTableWidgetItem(duration)
        dur_item.setTextAlignment(Qt.AlignCenter)
        self.files_table.setItem(row_count, 2, dur_item)
