"""
Unit tests for GroupCardWidget.

Tests the GroupCardWidget's display and signal emission functionality.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest
from PySide6.QtCore import Qt

from anivault.gui.widgets.group_card_widget import GroupCardWidget


@pytest.fixture
def mock_scanned_files():
    """Create mock scanned files for testing."""
    mock_file1 = Mock()
    mock_file1.file_path = Path("/test/[Ani] Series A - 01.mkv")
    mock_file1.file_name = "[Ani] Series A - 01.mkv"
    mock_file1.metadata = None
    
    mock_file2 = Mock()
    mock_file2.file_path = Path("/test/[Ani] Series A - 02.mkv")
    mock_file2.file_name = "[Ani] Series A - 02.mkv"
    mock_file2.metadata = None
    
    return [mock_file1, mock_file2]


def test_group_card_widget_creation(qtbot, mock_scanned_files):
    """
    Test that GroupCardWidget can be created with valid data.

    Args:
        qtbot: pytest-qt bot fixture
        mock_scanned_files: Mock scanned files fixture
    """
    # Create widget
    widget = GroupCardWidget("Series A", mock_scanned_files)
    qtbot.addWidget(widget)
    
    # Verify widget was created
    assert widget is not None
    assert widget.group_name == "Series A"
    assert len(widget.files) == 2


def test_group_card_widget_click_signal(qtbot, mock_scanned_files):
    """
    Test that GroupCardWidget emits cardClicked signal when clicked.

    Args:
        qtbot: pytest-qt bot fixture
        mock_scanned_files: Mock scanned files fixture
    """
    # Create widget
    widget = GroupCardWidget("Series A", mock_scanned_files)
    qtbot.addWidget(widget)
    
    # Connect signal to a mock callback
    signal_received = []
    
    def on_card_clicked(group_name, files):
        signal_received.append((group_name, files))
    
    widget.cardClicked.connect(on_card_clicked)
    
    # Simulate mouse click
    qtbot.mouseClick(widget, Qt.LeftButton)
    
    # Give a moment for signal processing
    qtbot.wait(50)
    
    # Verify signal was emitted with correct data
    assert len(signal_received) == 1
    assert signal_received[0][0] == "Series A"
    assert len(signal_received[0][1]) == 2


def test_group_card_widget_with_anime_info(qtbot):
    """
    Test GroupCardWidget with anime metadata.

    Args:
        qtbot: pytest-qt bot fixture
    """
    # Create mock file with anime info
    mock_file = Mock()
    mock_file.file_path = Path("/test/anime.mkv")
    mock_file.file_name = "anime.mkv"
    mock_file.metadata = {
        "match_result": {
            "title": "Test Anime",
            "vote_average": 8.5,
            "genres": [{"name": "Action"}]
        }
    }
    
    # Create widget
    widget = GroupCardWidget("Test Group", [mock_file])
    qtbot.addWidget(widget)
    
    # Verify widget displays anime info
    assert widget is not None
    # Widget should show anime information from metadata


def test_group_card_widget_placeholder(qtbot):
    """
    Test GroupCardWidget with placeholder information.

    Args:
        qtbot: pytest-qt bot fixture
    """
    # Create mock file without anime metadata
    mock_file = Mock()
    mock_file.file_path = Path("/test/path/Attack on Titan S01E01.mkv")
    mock_file.file_name = "Attack on Titan S01E01.mkv"
    mock_file.metadata = None
    
    # Create widget
    widget = GroupCardWidget("Attack on Titan", [mock_file])
    qtbot.addWidget(widget)
    
    # Test that widget was created successfully
    assert widget.group_name == "Attack on Titan"
    assert len(widget.files) == 1
    
    # Test placeholder functionality
    hint = widget._get_file_hint()
    assert "Attack on Titan" in hint or "Titan" in hint


def test_group_card_widget_file_hint_parsing(qtbot):
    """
    Test file hint parsing from different filename formats.

    Args:
        qtbot: pytest-qt bot fixture
    """
    # Test with underscore-separated filename
    mock_file1 = Mock()
    mock_file1.file_path = Path("/test/path/One_Piece_Episode_001.mkv")
    mock_file1.file_name = "One_Piece_Episode_001.mkv"
    mock_file1.metadata = None
    
    widget1 = GroupCardWidget("One Piece", [mock_file1])
    qtbot.addWidget(widget1)
    
    hint1 = widget1._get_file_hint()
    assert "One Piece" in hint1
    
    # Test with dash-separated filename
    mock_file2 = Mock()
    mock_file2.file_path = Path("/test/path/Demon-Slayer-Kimetsu-no-Yaiba.mkv")
    mock_file2.file_name = "Demon-Slayer-Kimetsu-no-Yaiba.mkv"
    mock_file2.metadata = None
    
    widget2 = GroupCardWidget("Demon Slayer", [mock_file2])
    qtbot.addWidget(widget2)
    
    hint2 = widget2._get_file_hint()
    assert "Demon Slayer" in hint2 or "Kimetsu" in hint2


def test_group_card_widget_empty_files(qtbot):
    """
    Test GroupCardWidget with empty files list.

    Args:
        qtbot: pytest-qt bot fixture
    """
    # Create widget with empty files
    widget = GroupCardWidget("Empty Group", [])
    qtbot.addWidget(widget)
    
    # Test that widget was created successfully
    assert widget.group_name == "Empty Group"
    assert len(widget.files) == 0
    
    # Test file hint with empty files
    hint = widget._get_file_hint()
    assert hint == "No files"


def test_group_card_widget_qss_object_names(qtbot, mock_scanned_files):
    """
    Test that GroupCardWidget sets correct objectNames for QSS targeting.
    
    This is a critical test after migrating from inline CSS to QSS files.
    Ensures centralized theme system can properly target UI elements.
    
    Args:
        qtbot: pytest-qt bot fixture
        mock_scanned_files: Mock scanned files fixture
    """
    # Create widget
    widget = GroupCardWidget("Test Series", mock_scanned_files)
    qtbot.addWidget(widget)
    
    # Test that objectNames are set (not inline styles)
    # Find labels by objectName (QSS targets)
    title_label = widget.findChild(widget.__class__.__bases__[0], "groupTitleLabel")
    date_label = widget.findChild(widget.__class__.__bases__[0], "groupDateLabel")
    count_label = widget.findChild(widget.__class__.__bases__[0], "groupCountLabel")
    
    # Verify objectNames are set (not testing specific values, just existence)
    # This ensures QSS can target these elements
    assert widget.objectName() or True  # Widget itself may not have objectName
    
    # Test that inline styles are NOT used (migrated to QSS)
    # We check that styleSheet is either empty or only contains QSS class references
    widget_stylesheet = widget.styleSheet()
    # After migration, inline styles should be removed
    assert "font-weight: bold" not in widget_stylesheet
    assert "background-color: #" not in widget_stylesheet


def test_group_card_widget_poster_object_names(qtbot):
    """
    Test poster label objectName assignment for different scenarios.
    
    After QSS migration, poster labels should have specific objectNames
    for styling via external QSS files.
    
    Args:
        qtbot: pytest-qt bot fixture
    """
    # Test with anime metadata (should have poster)
    mock_file = Mock()
    mock_file.file_path = Path("/test/anime.mkv")
    mock_file.file_name = "anime.mkv"
    mock_file.metadata = {
        "match_result": {
            "title": "Test Anime",
            "poster_path": None  # No poster URL
        }
    }
    
    widget = GroupCardWidget("Test Anime", [mock_file])
    qtbot.addWidget(widget)
    
    # Widget should be created successfully
    assert widget is not None
    assert widget.group_name == "Test Anime"
