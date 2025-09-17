"""Dark theme configuration for AniVault application."""


class DarkTheme:
    """Dark theme color palette and styles."""

    # Color palette
    COLORS = {
        # Primary colors
        "primary": "#3b82f6",  # Blue
        "primary_hover": "#2563eb",
        "primary_pressed": "#1d4ed8",
        # Secondary colors
        "secondary": "#10b981",  # Green
        "secondary_hover": "#059669",
        "secondary_pressed": "#047857",
        # Accent colors
        "accent": "#8b5cf6",  # Purple
        "accent_hover": "#7c3aed",
        "accent_pressed": "#6d28d9",
        # Background colors
        "bg_primary": "#1e293b",  # Dark blue-gray
        "bg_secondary": "#334155",  # Medium blue-gray
        "bg_tertiary": "#475569",  # Light blue-gray
        "bg_surface": "#0f172a",  # Darkest blue-gray
        # Text colors
        "text_primary": "#f1f5f9",  # White
        "text_secondary": "#94a3b8",  # Light gray
        "text_muted": "#64748b",  # Medium gray
        # Border colors
        "border_primary": "#475569",
        "border_secondary": "#64748b",
        # Status colors
        "success": "#10b981",
        "warning": "#f59e0b",
        "error": "#ef4444",
        "info": "#3b82f6",
        # Log level colors
        "log_info": "#94a3b8",  # Light grey
        "log_warning": "#fbbf24",  # Bright yellow
        "log_error": "#ef4444",  # Red
        "log_success": "#22c55e",  # Bright green
        # Status indicator colors
        "status_success": "#22c55e",
        "status_warning": "#eab308",
        "status_error": "#dc2626",
        # Label text colors
        "label_text": "#94a3b8",
        # Table colors
        "table_header": "#1e293b",
        "table_row_even": "#334155",
        "table_row_odd": "#2d3748",
        "table_selection": "#3b82f6",
        # Button colors
        "btn_danger": "#ef4444",
        "btn_danger_hover": "#dc2626",
        "btn_danger_pressed": "#b91c1c",
    }

    @classmethod
    def get_color(cls, color_name: str) -> str:
        """Get a color value by name."""
        return cls.COLORS.get(color_name, "#000000")

    @classmethod
    def get_main_window_style(cls) -> str:
        """Get main window stylesheet."""
        return f"""
        QMainWindow {{
            background-color: {cls.get_color('bg_primary')};
            color: {cls.get_color('text_primary')};
        }}
        """

    @classmethod
    def get_menu_bar_style(cls) -> str:
        """Get menu bar stylesheet."""
        return f"""
        QMenuBar {{
            background-color: {cls.get_color('bg_secondary')};
            color: {cls.get_color('text_primary')};
            border-bottom: 1px solid {cls.get_color('border_primary')};
            padding: 4px;
        }}
        QMenuBar::item {{
            background-color: transparent;
            padding: 6px 12px;
            border-radius: 4px;
        }}
        QMenuBar::item:selected {{
            background-color: {cls.get_color('bg_tertiary')};
        }}
        QMenu {{
            background-color: {cls.get_color('bg_secondary')};
            color: {cls.get_color('text_primary')};
            border: 1px solid {cls.get_color('border_primary')};
        }}
        QMenu::item:selected {{
            background-color: {cls.get_color('bg_tertiary')};
        }}
        """

    @classmethod
    def get_status_bar_style(cls) -> str:
        """Get status bar stylesheet."""
        return f"""
        QStatusBar {{
            background-color: {cls.get_color('bg_surface')};
            color: {cls.get_color('text_secondary')};
            border-top: 1px solid {cls.get_color('border_primary')};
        }}
        """

    @classmethod
    def get_group_box_style(cls) -> str:
        """Get group box stylesheet."""
        return f"""
        QGroupBox {{
            font-weight: bold;
            background-color: {cls.get_color('bg_secondary')};
            border: 2px solid {cls.get_color('border_primary')};
            border-radius: 16px;
            margin-top: 12px;
            padding-top: 12px;
            color: {cls.get_color('text_primary')};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 16px;
            padding: 4px 12px 4px 12px;
            background-color: {cls.get_color('bg_tertiary')};
            color: {cls.get_color('text_primary')};
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
        }}
        """

    @classmethod
    def get_line_edit_style(cls) -> str:
        """Get line edit stylesheet."""
        return f"""
        QLineEdit {{
            background-color: {cls.get_color('bg_secondary')};
            border: 1px solid {cls.get_color('border_primary')};
            border-radius: 6px;
            padding: 8px;
            color: {cls.get_color('text_primary')};
        }}
        QLineEdit:focus {{
            border-color: {cls.get_color('primary')};
        }}
        """

    @classmethod
    def get_button_style(cls, button_type: str = "primary") -> str:
        """Get button stylesheet based on type."""
        if button_type == "primary":
            return f"""
            QPushButton {{
                background-color: {cls.get_color('primary')};
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                color: {cls.get_color('text_primary')};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {cls.get_color('primary_hover')};
            }}
            QPushButton:pressed {{
                background-color: {cls.get_color('primary_pressed')};
            }}
            """
        elif button_type == "secondary":
            return f"""
            QPushButton {{
                background-color: {cls.get_color('secondary')};
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                color: {cls.get_color('text_primary')};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {cls.get_color('secondary_hover')};
            }}
            QPushButton:pressed {{
                background-color: {cls.get_color('secondary_pressed')};
            }}
            """
        elif button_type == "accent":
            return f"""
            QPushButton {{
                background-color: {cls.get_color('accent')};
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                color: {cls.get_color('text_primary')};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {cls.get_color('accent_hover')};
            }}
            QPushButton:pressed {{
                background-color: {cls.get_color('accent_pressed')};
            }}
            """
        elif button_type == "danger":
            return f"""
            QPushButton {{
                background-color: {cls.get_color('btn_danger')};
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                color: {cls.get_color('text_primary')};
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {cls.get_color('btn_danger_hover')};
            }}
            QPushButton:pressed {{
                background-color: {cls.get_color('btn_danger_pressed')};
            }}
            """
        else:  # default
            return f"""
            QPushButton {{
                background-color: {cls.get_color('bg_tertiary')};
                border: 1px solid {cls.get_color('border_secondary')};
                border-radius: 6px;
                padding: 6px 12px;
                color: {cls.get_color('text_primary')};
            }}
            QPushButton:hover {{
                background-color: {cls.get_color('border_secondary')};
            }}
            QPushButton:pressed {{
                background-color: {cls.get_color('bg_secondary')};
            }}
            """

    @classmethod
    def get_table_style(cls) -> str:
        """Get table widget stylesheet."""
        return f"""
        QTableWidget {{
            background-color: {cls.get_color('bg_secondary')} !important;
            border: 1px solid {cls.get_color('border_primary')};
            border-radius: 8px;
            gridline-color: {cls.get_color('border_primary')};
            color: {cls.get_color('text_primary')} !important;
            selection-background-color: {cls.get_color('table_selection')};
            alternate-background-color: {cls.get_color('table_row_odd')};
        }}
        QTableWidget::item {{
            padding: 8px;
            border-bottom: 1px solid {cls.get_color('border_primary')};
            background-color: {cls.get_color('bg_secondary')} !important;
            color: {cls.get_color('text_primary')} !important;
        }}
        QTableWidget::item:alternate {{
            background-color: {cls.get_color('table_row_odd')} !important;
            color: {cls.get_color('text_primary')} !important;
        }}
        QTableWidget::item:selected {{
            background-color: {cls.get_color('table_selection')} !important;
            color: {cls.get_color('text_primary')} !important;
        }}
        QTableWidget::item:selected:alternate {{
            background-color: {cls.get_color('table_selection')} !important;
            color: {cls.get_color('text_primary')} !important;
        }}
        QHeaderView::section {{
            background-color: {cls.get_color('table_header')} !important;
            color: {cls.get_color('text_primary')} !important;
            padding: 8px;
            border: none;
            border-right: 1px solid {cls.get_color('border_primary')};
            font-weight: bold;
        }}
        QHeaderView::section:horizontal {{
            background-color: {cls.get_color('table_header')} !important;
            color: {cls.get_color('text_primary')} !important;
        }}
        QHeaderView::section:vertical {{
            background-color: {cls.get_color('table_header')} !important;
            color: {cls.get_color('text_primary')} !important;
        }}

        /* Style the corner cell (top-left intersection) */
        QHeaderView::corner {{
            background-color: {cls.get_color('table_header')} !important;
            color: {cls.get_color('text_primary')} !important;
            border: none;
        }}

        /* Alternative approach for corner button */
        QTableCornerButton::section {{
            background-color: {cls.get_color('table_header')} !important;
            color: {cls.get_color('text_primary')} !important;
            border: none;
        }}

        /* Force all table elements to use dark theme */
        QTableWidget * {{
            background-color: {cls.get_color('bg_secondary')} !important;
            color: {cls.get_color('text_primary')} !important;
        }}

        /* Override any system default colors */
        QTableWidget::item:!alternate {{
            background-color: {cls.get_color('bg_secondary')} !important;
            color: {cls.get_color('text_primary')} !important;
        }}
        """

    @classmethod
    def get_text_edit_style(cls) -> str:
        """Get text edit stylesheet."""
        return f"""
        QTextEdit {{
            background-color: {cls.get_color('bg_surface')};
            border: 1px solid {cls.get_color('border_primary')};
            border-radius: 6px;
            color: {cls.get_color('text_secondary')};
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 11px;
            padding: 8px;
        }}
        """

    @classmethod
    def get_scroll_area_style(cls) -> str:
        """Get scroll area stylesheet."""
        return """
        QScrollArea {
            border: none;
            background-color: transparent;
        }
        """

    @classmethod
    def get_frame_style(cls, frame_type: str = "default") -> str:
        """Get frame stylesheet based on type."""
        if frame_type == "card":
            return f"""
            QFrame {{
                background-color: {cls.get_color('bg_secondary')};
                border: 1px solid {cls.get_color('border_primary')};
                border-radius: 8px;
                padding: 12px;
            }}
            """
        elif frame_type == "info":
            return f"""
            QFrame {{
                background-color: {cls.get_color('bg_secondary')};
                border: 1px solid {cls.get_color('border_primary')};
                border-radius: 6px;
                padding: 8px;
            }}
            """
        else:  # default
            return f"""
            QFrame {{
                background-color: {cls.get_color('bg_secondary')};
                border: 1px solid {cls.get_color('border_primary')};
                border-radius: 6px;
                padding: 8px;
            }}
            """

    @classmethod
    def get_label_style(cls, label_type: str = "default") -> str:
        """Get label stylesheet based on type."""
        if label_type == "title":
            return f"""
            QLabel {{
                font-size: 18px;
                font-weight: bold;
                color: {cls.get_color('primary')};
                padding: 8px;
                background-color: {cls.get_color('bg_secondary')};
                border-radius: 6px;
            }}
            """
        elif label_type == "field_name":
            return f"""
            QLabel {{
                font-weight: bold;
                color: {cls.get_color('text_secondary')};
                font-size: 12px;
            }}
            """
        elif label_type == "field_value":
            return f"""
            QLabel {{
                color: {cls.get_color('text_primary')};
                font-size: 14px;
            }}
            """
        elif label_type == "stat_value":
            return f"""
            QLabel {{
                font-size: 24px;
                font-weight: bold;
                color: {cls.get_color('primary')};
            }}
            """
        elif label_type == "stat_label":
            return f"""
            QLabel {{
                font-size: 12px;
                color: {cls.get_color('text_secondary')};
            }}
            """
        else:  # default
            return f"""
            QLabel {{
                color: {cls.get_color('text_primary')};
            }}
            """

    @classmethod
    def get_complete_style(cls) -> str:
        """Get complete application stylesheet."""
        return (
            f"""
        /* Global application styles */
        QApplication {{
            background-color: {cls.get_color('bg_primary')};
            color: {cls.get_color('text_primary')};
        }}

        /* Main window styles */
        QMainWindow {{
            background-color: {cls.get_color('bg_primary')};
            color: {cls.get_color('text_primary')};
        }}

        /* Widget styles */
        QWidget {{
            background-color: {cls.get_color('bg_primary')};
            color: {cls.get_color('text_primary')};
        }}

        /* Scroll bar styles */
        QScrollBar:vertical {{
            background-color: {cls.get_color('bg_secondary')};
            width: 12px;
            border-radius: 6px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {cls.get_color('bg_tertiary')};
            border-radius: 6px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {cls.get_color('border_secondary')};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}

        QScrollBar:horizontal {{
            background-color: {cls.get_color('bg_secondary')};
            height: 12px;
            border-radius: 6px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {cls.get_color('bg_tertiary')};
            border-radius: 6px;
            min-width: 20px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: {cls.get_color('border_secondary')};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}

        /* Splitter styles */
        QSplitter {{
            background-color: {cls.get_color('bg_primary')};
        }}
        QSplitter::handle {{
            background-color: {cls.get_color('border_primary')};
        }}
        QSplitter::handle:horizontal {{
            width: 2px;
        }}
        QSplitter::handle:vertical {{
            height: 2px;
        }}

        /* Tooltip styles */
        QToolTip {{
            background-color: {cls.get_color('bg_secondary')};
            color: {cls.get_color('text_primary')};
            border: 1px solid {cls.get_color('border_primary')};
            border-radius: 4px;
            padding: 4px;
        }}

        """
            + cls.get_main_window_style()
            + cls.get_menu_bar_style()
            + cls.get_status_bar_style()
        )

    @classmethod
    def get_log_level_color(cls, level: str) -> str:
        """Get color for specific log level."""
        level_colors = {
            "INFO": cls.get_color("log_info"),
            "WARNING": cls.get_color("log_warning"),
            "ERROR": cls.get_color("log_error"),
            "SUCCESS": cls.get_color("log_success"),
        }
        return level_colors.get(level.upper(), cls.get_color("log_info"))

    @classmethod
    def get_status_color(cls, status: str) -> str:
        """Get color for specific status."""
        status_colors = {
            "success": cls.get_color("status_success"),
            "warning": cls.get_color("status_warning"),
            "error": cls.get_color("status_error"),
            "completed": cls.get_color("status_success"),
            "pending": cls.get_color("status_warning"),
            "failed": cls.get_color("status_error"),
            # Uppercase versions
            "SUCCESS": cls.get_color("status_success"),
            "WARNING": cls.get_color("status_warning"),
            "ERROR": cls.get_color("status_error"),
            "COMPLETED": cls.get_color("status_success"),
            "PENDING": cls.get_color("status_warning"),
            "FAILED": cls.get_color("status_error"),
            # Korean status names
            "완료": cls.get_color("status_success"),
            "대기": cls.get_color("status_warning"),
            "오류": cls.get_color("status_error"),
            "실패": cls.get_color("status_error"),
        }
        return status_colors.get(status, cls.get_color("text_secondary"))

    @classmethod
    def get_label_text_style(cls) -> str:
        """Get style for label text."""
        return f"""
        QLabel {{
            color: {cls.get_color('label_text')};
        }}
        """

    @classmethod
    def get_tab_widget_style(cls) -> str:
        """Get tab widget stylesheet."""
        return f"""
        QTabWidget::pane {{
            border: 1px solid {cls.get_color('border_primary')};
            background-color: {cls.get_color('bg_primary')};
        }}
        QTabBar::tab {{
            background-color: {cls.get_color('bg_secondary')};
            color: {cls.get_color('text_primary')};
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }}
        QTabBar::tab:selected {{
            background-color: {cls.get_color('bg_primary')};
            color: {cls.get_color('primary')};
        }}
        QTabBar::tab:hover {{
            background-color: {cls.get_color('bg_tertiary')};
        }}
        """

    @classmethod
    def get_progress_bar_style(cls) -> str:
        """Get progress bar stylesheet."""
        return f"""
        QProgressBar {{
            border: 2px solid {cls.get_color('border_primary')};
            border-radius: 5px;
            text-align: center;
            background-color: {cls.get_color('bg_secondary')};
            color: {cls.get_color('text_primary')};
        }}
        QProgressBar::chunk {{
            background-color: {cls.get_color('primary')};
            border-radius: 3px;
        }}
        """
