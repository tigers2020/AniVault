"""Test ScanController with LinkedHashTable optimization."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from anivault.core.data_structures.linked_hash_table import LinkedHashTable
from src.anivault.gui.controllers.scan_controller import ScanController
from src.anivault.gui.models import FileItem
from anivault.shared.metadata_models import FileMetadata, TMDBMatchResult


class TestScanControllerLinkedHashTable:
    """Test ScanController with LinkedHashTable optimization."""

    @pytest.fixture
    def scan_controller(self):
        """Create ScanController instance for testing."""
        return ScanController()

    @pytest.fixture
    def sample_file_items(self):
        """Create sample FileItem objects for testing."""
        file_items = []

        # Create FileItem objects
        file_paths = [
            Path("test_anime_s01e01.mkv"),
            Path("test_anime_s01e02.mkv"),
            Path("another_anime_s01e01.mkv"),
        ]

        for file_path in file_paths:
            file_item = FileItem(file_path)
            file_item.metadata = FileMetadata(
                title="Test Anime"
                if "test_anime" in str(file_path)
                else "Another Anime",
                file_path=file_path,
                file_type="mkv",
                tmdb_id=12345 if "test_anime" in str(file_path) else 67890,
                media_type="tv",
                genres=["Animation", "Action"]
                if "test_anime" in str(file_path)
                else ["Animation", "Comedy"],
                overview="A test anime series"
                if "test_anime" in str(file_path)
                else "Another test anime series",
                vote_average=8.5 if "test_anime" in str(file_path) else 7.8,
                poster_path="/poster.jpg"
                if "test_anime" in str(file_path)
                else "/poster2.jpg",
            )
            file_items.append(file_item)

        return file_items

    def test_group_matched_files_returns_linkedhashtable(
        self, scan_controller, sample_file_items
    ):
        """Test that _group_matched_files returns LinkedHashTable."""
        matched_files = sample_file_items[:2]  # First two files with same TMDB ID

        result = scan_controller._group_matched_files(matched_files)

        # Check that result has LinkedHashTable methods
        assert hasattr(result, "put")
        assert hasattr(result, "get")
        assert hasattr(result, "__iter__")
        assert hasattr(result, "__len__")

        # Check that it contains the expected data
        assert len(result) == 1
        assert "Test Anime" in result
        assert len(result.get("Test Anime")) == 2

    def test_group_files_by_filename_returns_linkedhashtable(
        self, scan_controller, sample_file_items
    ):
        """Test that _group_files_by_filename returns LinkedHashTable."""
        unmatched_files = sample_file_items  # All files

        # Mock the file_grouper to avoid the BestMatcherStrategy issue
        with patch.object(scan_controller.file_grouper, "group_files") as mock_group:
            from src.anivault.core.file_grouper.models import Group

            mock_group.return_value = [Group(title="Test Group", files=[])]

            result = scan_controller._group_files_by_filename(unmatched_files)

            assert isinstance(result, LinkedHashTable)
            assert len(result) > 0

    def test_merge_unmatched_files_with_linkedhashtable(
        self, scan_controller, sample_file_items
    ):
        """Test that _merge_unmatched_files works with LinkedHashTable."""
        # Create initial LinkedHashTable
        initial_groups = LinkedHashTable[str, list[FileItem]]()
        initial_groups.put("Existing Group", [sample_file_items[0]])

        unmatched_files = [sample_file_items[1], sample_file_items[2]]

        # Mock the file_grouper to avoid the BestMatcherStrategy issue
        with patch.object(scan_controller.file_grouper, "group_files") as mock_group:
            from src.anivault.core.file_grouper.models import Group

            mock_group.return_value = [Group(title="Test Group", files=[])]

            result = scan_controller._merge_unmatched_files(
                initial_groups, unmatched_files
            )

            assert isinstance(result, LinkedHashTable)
            assert len(result) >= 1

    def test_convert_to_scanned_files_with_linkedhashtable(
        self, scan_controller, sample_file_items
    ):
        """Test that _convert_to_scanned_files works with LinkedHashTable."""
        # Create LinkedHashTable input
        input_groups = LinkedHashTable[str, list[FileItem]]()
        input_groups.put("Test Group", sample_file_items[:2])

        # Mock the parser to return a ParsingResult
        from src.anivault.core.parser.models import ParsingResult, ParsingAdditionalInfo

        with patch.object(scan_controller.parser, "parse") as mock_parse:
            mock_parse.return_value = ParsingResult(
                title="Test Anime",
                episode=None,
                season=None,
                quality=None,
                source=None,
                codec=None,
                audio=None,
                release_group=None,
                confidence=0.8,
                parser_used="test",
                additional_info=ParsingAdditionalInfo(),
            )

            result = scan_controller._convert_to_scanned_files(input_groups)

            assert isinstance(result, LinkedHashTable)
            assert len(result) == 1
            assert "Test Group" in result
            scanned_files = result.get("Test Group")
            assert len(scanned_files) == 2

    def test_group_files_by_tmdb_title_returns_linkedhashtable(
        self, scan_controller, sample_file_items
    ):
        """Test that group_files_by_tmdb_title returns LinkedHashTable."""
        # Mock the file_grouper to avoid the BestMatcherStrategy issue
        with patch.object(scan_controller.file_grouper, "group_files") as mock_group:
            from src.anivault.core.file_grouper.models import Group

            mock_group.return_value = [Group(title="Test Group", files=[])]

            # Mock the parser to return a ParsingResult
            from src.anivault.core.parser.models import (
                ParsingResult,
                ParsingAdditionalInfo,
            )

            with patch.object(scan_controller.parser, "parse") as mock_parse:
                mock_parse.return_value = ParsingResult(
                    title="Test Anime",
                    episode=None,
                    season=None,
                    quality=None,
                    source=None,
                    codec=None,
                    audio=None,
                    release_group=None,
                    confidence=0.8,
                    parser_used="test",
                    additional_info=ParsingAdditionalInfo(),
                )

                result = scan_controller.group_files_by_tmdb_title(sample_file_items)

                assert isinstance(result, LinkedHashTable)
                assert len(result) >= 1

    def test_linkedhashtable_performance_characteristics(
        self, scan_controller, sample_file_items
    ):
        """Test that LinkedHashTable provides O(1) operations."""
        groups = scan_controller._group_matched_files(sample_file_items)

        # Test O(1) get operation
        import time

        start_time = time.perf_counter()
        for _ in range(1000):
            groups.get("Test Anime")
        end_time = time.perf_counter()

        # Should be very fast (O(1))
        assert (end_time - start_time) < 0.1  # Should complete in under 100ms

    def test_linkedhashtable_maintains_insertion_order(
        self, scan_controller, sample_file_items
    ):
        """Test that LinkedHashTable maintains insertion order."""
        groups = scan_controller._group_matched_files(sample_file_items)

        # Get all items in order
        items = list(groups)

        # Should maintain insertion order
        assert len(items) > 0
        # First item should be the first group added
        assert items[0][0] == "Test Anime"

    def test_tmdb_match_result_dataclass_validation(self):
        """Test that TMDBMatchResult dataclass validates fields correctly."""
        # Valid TMDBMatchResult
        valid_result = TMDBMatchResult(
            id=12345,
            title="Test Anime",
            media_type="tv",
            genres=["Animation", "Action"],
            overview="A test anime",
            vote_average=8.5,
            poster_path="/poster.jpg",
        )

        assert valid_result.id == 12345
        assert valid_result.title == "Test Anime"
        assert valid_result.media_type == "tv"
        assert valid_result.genres == ["Animation", "Action"]
        assert valid_result.overview == "A test anime"
        assert valid_result.vote_average == 8.5
        assert valid_result.poster_path == "/poster.jpg"

    def test_tmdb_match_result_validation_errors(self):
        """Test that TMDBMatchResult raises validation errors for invalid data."""
        # Empty title should raise ValueError
        with pytest.raises(ValueError, match="title cannot be empty"):
            TMDBMatchResult(id=12345, title="", media_type="tv")

        # Invalid ID should raise ValueError
        with pytest.raises(ValueError, match="id must be positive"):
            TMDBMatchResult(id=0, title="Test Anime", media_type="tv")

        # Invalid vote_average should raise ValueError
        with pytest.raises(
            ValueError, match="vote_average must be between 0.0 and 10.0"
        ):
            TMDBMatchResult(
                id=12345, title="Test Anime", media_type="tv", vote_average=11.0
            )

    def test_scan_controller_uses_tmdb_match_result_dataclass(
        self, scan_controller, sample_file_items
    ):
        """Test that ScanController uses TMDBMatchResult dataclass instead of dict."""
        # Mock the parser to return a ParsingResult with additional_info
        from src.anivault.core.parser.models import ParsingResult, ParsingAdditionalInfo

        with patch.object(scan_controller.parser, "parse") as mock_parse:
            parsing_result = ParsingResult(
                title="Test Anime",
                episode=None,
                season=None,
                quality=None,
                source=None,
                codec=None,
                audio=None,
                release_group=None,
                confidence=0.8,
                parser_used="test",
                additional_info=ParsingAdditionalInfo(),
            )
            mock_parse.return_value = parsing_result

            # Test _convert_to_scanned_files method
            input_groups = LinkedHashTable[str, list[FileItem]]()
            input_groups.put("Test Group", sample_file_items[:1])

            result = scan_controller._convert_to_scanned_files(input_groups)

            # Check that the result contains TMDBMatchResult dataclass
            scanned_files = result.get("Test Group")  # Use the actual key from result
            assert len(scanned_files) == 1

            scanned_file = scanned_files[0]
            match_result = scanned_file.metadata.additional_info.match_result

            # Should be TMDBMatchResult dataclass, not dict
            assert match_result is not None
            assert hasattr(match_result, "id")
            assert hasattr(match_result, "title")
            assert match_result.id == 12345
            assert match_result.title == "Test Anime"
