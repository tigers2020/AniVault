#!/usr/bin/env python3
"""TMDB Comprehensive Search Example

This example demonstrates the new comprehensive TMDB search flow:
1. TMDB TV search → if no results → TMDB Movie search
2. If no results → recursive word reduction until 1 word left
3. If still no results → manual search dialog
4. If 2+ results → manual selection dialog

Usage:
    python examples/tmdb_comprehensive_search_example.py
"""

import os
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.tmdb_client import TMDBError, create_tmdb_client_with_config
from gui.tmdb_selection_dialog import TMDBSelectionDialog


class TMDBSearchExample(QMainWindow):
    """Example application demonstrating TMDB comprehensive search."""

    def __init__(self):
        super().__init__()
        self.tmdb_client = None
        self.setup_ui()
        self.setup_tmdb_client()

    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("TMDB Comprehensive Search Example")
        self.setGeometry(100, 100, 600, 400)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)

        # Title
        title_label = QLabel("TMDB Comprehensive Search Example")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter anime title to search...")
        self.search_input.returnPressed.connect(self.perform_search)
        layout.addWidget(self.search_input)

        # Search button
        self.search_btn = QPushButton("Search with Comprehensive Flow")
        self.search_btn.clicked.connect(self.perform_search)
        layout.addWidget(self.search_btn)

        # Manual search button
        self.manual_search_btn = QPushButton("Manual Search Dialog")
        self.manual_search_btn.clicked.connect(self.show_manual_search)
        layout.addWidget(self.manual_search_btn)

        # Status label
        self.status_label = QLabel("Enter a search query and click search.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # Add stretch to push everything to the top
        layout.addStretch()

    def setup_tmdb_client(self):
        """Setup TMDB client with API key."""
        # You need to set your TMDB API key here
        api_key = os.getenv("TMDB_API_KEY")
        if not api_key:
            self.status_label.setText("Error: TMDB_API_KEY environment variable not set!")
            self.status_label.setStyleSheet("color: red;")
            return

        try:
            self.tmdb_client = create_tmdb_client_with_config(
                api_key=api_key, language="ko-KR", fallback_language="en-US"
            )
            self.status_label.setText("TMDB client initialized successfully. Ready to search!")
            self.status_label.setStyleSheet("color: green;")
        except TMDBError as e:
            self.status_label.setText(f"Error initializing TMDB client: {e}")
            self.status_label.setStyleSheet("color: red;")

    def perform_search(self):
        """Perform comprehensive search."""
        query = self.search_input.text().strip()
        if not query:
            self.status_label.setText("Please enter a search query.")
            return

        if not self.tmdb_client:
            self.status_label.setText("TMDB client not initialized!")
            return

        self.status_label.setText(f"Searching for: '{query}'...")
        self.search_btn.setEnabled(False)

        try:
            # Use the new comprehensive search
            search_result, needs_manual_selection = self.tmdb_client.search_comprehensive(
                query, language="ko-KR", min_quality=0.3
            )

            if search_result and search_result.results:
                if needs_manual_selection:
                    self.status_label.setText(
                        f"Found {len(search_result.results)} results for '{query}'. "
                        f"Manual selection needed. (Strategy: {search_result.strategy_used.value})"
                    )
                    # Show selection dialog
                    self.show_selection_dialog(search_result)
                else:
                    self.status_label.setText(
                        f"Found 1 good result for '{query}'. "
                        f"(Strategy: {search_result.strategy_used.value})"
                    )
                    # Show the single result
                    self.show_single_result(search_result.results[0])
            else:
                self.status_label.setText(f"No results found for '{query}'. Try manual search.")
                self.status_label.setStyleSheet("color: orange;")

        except Exception as e:
            self.status_label.setText(f"Search error: {e!s}")
            self.status_label.setStyleSheet("color: red;")
        finally:
            self.search_btn.setEnabled(True)

    def show_selection_dialog(self, search_result):
        """Show selection dialog for multiple results."""
        if self.tmdb_client is None or self.tmdb_client.config is None:
            return
        dialog = TMDBSelectionDialog(parent=self, api_key=self.tmdb_client.config.api_key)

        dialog.set_initial_search(search_result.query_used, search_result.results)

        if dialog.exec_() == dialog.Accepted:
            selected_result = dialog.get_selected_result()
            if selected_result:
                self.show_single_result(selected_result)

    def show_manual_search(self):
        """Show manual search dialog."""
        query = self.search_input.text().strip()

        if self.tmdb_client is None or self.tmdb_client.config is None:
            return
        dialog = TMDBSelectionDialog(parent=self, api_key=self.tmdb_client.config.api_key)

        dialog.set_initial_search(query, [])

        if dialog.exec_() == dialog.Accepted:
            selected_result = dialog.get_selected_result()
            if selected_result:
                self.show_single_result(selected_result)

    def show_single_result(self, result):
        """Show details of a single result."""
        title = result.get("name", "Unknown Title")
        original_title = result.get("original_name", title)
        first_air_date = result.get("first_air_date", "Unknown")
        overview = result.get("overview", "No overview available")

        # Truncate overview if too long
        if len(overview) > 200:
            overview = overview[:200] + "..."

        self.status_label.setText(
            f"Selected: {title}\n"
            f"Original: {original_title}\n"
            f"First Air Date: {first_air_date}\n"
            f"Overview: {overview}"
        )
        self.status_label.setStyleSheet("color: blue;")


def main():
    """Main function."""
    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("TMDB Comprehensive Search Example")
    app.setApplicationVersion("1.0")

    # Create and show main window
    window = TMDBSearchExample()
    window.show()

    # Run the application
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
