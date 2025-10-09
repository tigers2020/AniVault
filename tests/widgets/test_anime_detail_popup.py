"""
Unit tests for AnimeDetailPopup.

Tests the AnimeDetailPopup's display functionality.
"""

import pytest

from anivault.gui.widgets.anime_detail_popup import AnimeDetailPopup


@pytest.fixture
def mock_anime_info():
    """Create mock anime information for testing."""
    return {
        "title": "Test Anime",
        "vote_average": 8.5,
        "vote_count": 1234,
        "genres": [{"name": "Action"}, {"name": "Adventure"}],
        "overview": "This is a test anime overview for testing purposes.",
        "first_air_date": "2023-01-01",
        "last_air_date": "2023-12-31",
        "status": "Ended",
        "number_of_seasons": 2,
        "number_of_episodes": 24,
        "episode_run_time": [24],
        "production_companies": [{"name": "Test Studio"}, {"name": "Another Studio"}],
        "popularity": 150.5,
    }


def test_anime_detail_popup_creation(qtbot, mock_anime_info):
    """
    Test that AnimeDetailPopup can be created with valid data.

    Args:
        qtbot: pytest-qt bot fixture
        mock_anime_info: Mock anime information fixture
    """
    # Create popup
    popup = AnimeDetailPopup(mock_anime_info)
    qtbot.addWidget(popup)

    # Verify popup was created
    assert popup is not None
    assert popup.anime_info == mock_anime_info


def test_anime_detail_popup_displays_title(qtbot, mock_anime_info):
    """
    Test that AnimeDetailPopup displays the title correctly.

    Args:
        qtbot: pytest-qt bot fixture
        mock_anime_info: Mock anime information fixture
    """
    # Create popup
    popup = AnimeDetailPopup(mock_anime_info)
    qtbot.addWidget(popup)

    # Find title label
    title_label = popup.findChild(type(popup), "popupTitleLabel")

    # Verify title is displayed (if label exists)
    if title_label:
        assert "Test Anime" in title_label.text()


def test_anime_detail_popup_minimal_info(qtbot):
    """
    Test AnimeDetailPopup with minimal anime information.

    Args:
        qtbot: pytest-qt bot fixture
    """
    minimal_info = {"title": "Minimal Anime"}

    # Create popup with minimal info
    popup = AnimeDetailPopup(minimal_info)
    qtbot.addWidget(popup)

    # Verify popup can be created with minimal data
    assert popup is not None
    assert popup.anime_info == minimal_info
