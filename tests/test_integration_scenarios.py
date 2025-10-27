"""Integration tests for OptimizedFileOrganizer end-to-end scenarios."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
from typing import List

from src.anivault.core.models import ScannedFile, OperationType
from src.anivault.core.parser.models import ParsingResult, ParsingAdditionalInfo
from src.anivault.core.organizer.file_organizer import OptimizedFileOrganizer


class TestIntegrationScenarios:
    """Integration test scenarios for OptimizedFileOrganizer."""

    @pytest.fixture
    def temp_directories(self):
        """Create temporary directories for testing."""
        source_dir = tempfile.mkdtemp(prefix="anivault_test_source_")
        dest_dir = tempfile.mkdtemp(prefix="anivault_test_dest_")
        duplicates_dir = tempfile.mkdtemp(prefix="anivault_test_duplicates_")

        yield {
            "source": Path(source_dir),
            "destination": Path(dest_dir),
            "duplicates": Path(duplicates_dir)
        }

        # Cleanup
        shutil.rmtree(source_dir, ignore_errors=True)
        shutil.rmtree(dest_dir, ignore_errors=True)
        shutil.rmtree(duplicates_dir, ignore_errors=True)

    @pytest.fixture
    def mock_settings(self, temp_directories):
        """Create mock settings with test directories."""
        settings = Mock()
        settings.app = Mock()
        settings.app.organizer = Mock()
        settings.app.organizer.destination_path = str(temp_directories["destination"])
        return settings

    @pytest.fixture
    def mock_log_manager(self):
        """Create mock log manager."""
        return Mock()

    @pytest.fixture
    def organizer(self, mock_log_manager, mock_settings):
        """Create OptimizedFileOrganizer instance for testing."""
        return OptimizedFileOrganizer(
            log_manager=mock_log_manager,
            settings=mock_settings
        )

    def create_test_files(self, temp_dirs: dict, file_configs: List[dict]) -> List[ScannedFile]:
        """Create test files and return ScannedFile objects."""
        scanned_files = []

        for i, config in enumerate(file_configs):
            # Create file
            file_path = temp_dirs["source"] / config["filename"]
            file_path.write_text(config.get("content", f"Test content {i}"))

            # Create metadata
            metadata = ParsingResult(
                title=config.get("title", "Test Anime"),
                season=config.get("season", 1),
                episode=config.get("episode", i + 1),
                quality=config.get("quality", "1080p"),
                release_group=config.get("release_group", "TEST"),
                confidence=config.get("confidence", 0.9),
                parser_used="test",
                additional_info=ParsingAdditionalInfo()
            )

            # Create ScannedFile
            scanned_file = ScannedFile(
                file_path=file_path,
                metadata=metadata,
                file_size=config.get("size", 1000000),
                last_modified=1640995200.0 + i
            )

            scanned_files.append(scanned_file)

        return scanned_files

    def test_scenario_1_single_anime_series(self, organizer, temp_directories):
        """Test scenario: Single anime series with multiple episodes."""
        # Create test files
        file_configs = [
            {"filename": "anime_ep01_1080p.mkv", "title": "Test Anime", "episode": 1, "quality": "1080p"},
            {"filename": "anime_ep02_1080p.mkv", "title": "Test Anime", "episode": 2, "quality": "1080p"},
            {"filename": "anime_ep03_1080p.mkv", "title": "Test Anime", "episode": 3, "quality": "1080p"},
        ]

        test_files = self.create_test_files(temp_directories, file_configs)

        # Add files to organizer
        for file in test_files:
            organizer.add_file(file)

        # Verify files are cached
        assert organizer.file_count == 3

        # Test duplicate detection (should find no duplicates)
        duplicates = organizer.find_duplicates()
        assert len(duplicates) == 0

        # Test plan generation
        plan = organizer.generate_plan(test_files)
        assert len(plan) == 3

        # All operations should be MOVE operations
        for operation in plan:
            assert operation.operation_type == OperationType.MOVE
            assert "Test_Anime" in str(operation.destination_path)

    def test_scenario_2_duplicate_files(self, organizer, temp_directories):
        """Test scenario: Duplicate files with different qualities."""
        # Create test files with duplicates
        file_configs = [
            {"filename": "anime_ep01_720p.mkv", "title": "Test Anime", "episode": 1, "quality": "720p", "size": 500000},
            {"filename": "anime_ep01_1080p.mkv", "title": "Test Anime", "episode": 1, "quality": "1080p", "size": 1000000},
            {"filename": "anime_ep01_4K.mkv", "title": "Test Anime", "episode": 1, "quality": "4K", "size": 2000000},
        ]

        test_files = self.create_test_files(temp_directories, file_configs)

        # Add files to organizer
        for file in test_files:
            organizer.add_file(file)

        # Verify files are cached
        assert organizer.file_count == 3

        # Test duplicate detection
        duplicates = organizer.find_duplicates()
        assert len(duplicates) == 1  # One group of duplicates
        assert len(duplicates[0]) == 3  # Three files in the group

        # Test plan generation
        plan = organizer.generate_plan(test_files)
        assert len(plan) == 3

        # Should have 3 MOVE operations (all files should be moved)
        move_ops = [op for op in plan if op.operation_type == OperationType.MOVE]

        assert len(move_ops) == 3

        # All files should be moved to organized structure
        for operation in move_ops:
            assert operation.operation_type == OperationType.MOVE
            # Check that the path contains either "Test Anime" or "Test_Anime"
            path_str = str(operation.destination_path)
            assert "Test Anime" in path_str or "Test_Anime" in path_str

    def test_scenario_3_mixed_media_types(self, organizer, temp_directories):
        """Test scenario: Mixed media types (anime, movies, etc.)."""
        # Create test files with different media types
        file_configs = [
            {"filename": "anime_ep01_1080p.mkv", "title": "Test Anime", "episode": 1, "quality": "1080p"},
            {"filename": "movie_2023_1080p.mkv", "title": "Test Movie", "episode": None, "quality": "1080p"},
            {"filename": "anime_ep02_1080p.mkv", "title": "Test Anime", "episode": 2, "quality": "1080p"},
        ]

        test_files = self.create_test_files(temp_directories, file_configs)

        # Add files to organizer
        for file in test_files:
            organizer.add_file(file)

        # Verify files are cached
        assert organizer.file_count == 3

        # Test duplicate detection (should find no duplicates)
        duplicates = organizer.find_duplicates()
        assert len(duplicates) == 0

        # Test plan generation
        plan = organizer.generate_plan(test_files)
        assert len(plan) == 3

        # All operations should be MOVE operations
        for operation in plan:
            assert operation.operation_type == OperationType.MOVE

    def test_scenario_4_large_dataset(self, organizer, temp_directories):
        """Test scenario: Large dataset with many files."""
        # Create many test files
        file_configs = []
        for i in range(100):
            file_configs.append({
                "filename": f"anime_ep{i+1:02d}_1080p.mkv",
                "title": "Test Anime",
                "episode": i + 1,
                "quality": "1080p",
                "size": 1000000 + i * 1000
            })

        test_files = self.create_test_files(temp_directories, file_configs)

        # Add files to organizer
        for file in test_files:
            organizer.add_file(file)

        # Verify files are cached
        assert organizer.file_count == 100

        # Test duplicate detection (should find no duplicates)
        duplicates = organizer.find_duplicates()
        assert len(duplicates) == 0

        # Test plan generation
        plan = organizer.generate_plan(test_files)
        assert len(plan) == 100

        # All operations should be MOVE operations
        for operation in plan:
            assert operation.operation_type == OperationType.MOVE

    def test_scenario_5_organize_execution(self, organizer, temp_directories):
        """Test scenario: Full organize execution (dry run)."""
        # Create test files
        file_configs = [
            {"filename": "anime_ep01_1080p.mkv", "title": "Test Anime", "episode": 1, "quality": "1080p"},
            {"filename": "anime_ep02_1080p.mkv", "title": "Test Anime", "episode": 2, "quality": "1080p"},
        ]

        test_files = self.create_test_files(temp_directories, file_configs)

        # Test full organize execution (dry run)
        results = organizer.organize(test_files, dry_run=True)

        # Should return results
        assert results is not None
        assert len(results) == 2

        # All results should be FileOperation objects (not OperationResult)
        for result in results:
            assert hasattr(result, 'operation_type')
            assert hasattr(result, 'source_path')
            assert hasattr(result, 'destination_path')

    def test_scenario_6_error_handling(self, organizer, temp_directories):
        """Test scenario: Error handling with invalid files."""
        # Create test files with some invalid data
        file_configs = [
            {"filename": "valid_file.mkv", "title": "Valid Anime", "episode": 1, "quality": "1080p"},
            {"filename": "invalid_file.txt", "title": None, "episode": None, "quality": None},  # Invalid metadata
        ]

        test_files = self.create_test_files(temp_directories, file_configs)

        # Add files to organizer (should handle errors gracefully)
        for file in test_files:
            try:
                organizer.add_file(file)
            except Exception:
                # Some files might fail to add, which is expected
                pass

        # Should have at least one file
        assert organizer.file_count >= 1

        # Test plan generation (should handle errors gracefully)
        plan = organizer.generate_plan(test_files)
        assert isinstance(plan, list)

    def test_scenario_7_clear_cache(self, organizer, temp_directories):
        """Test scenario: Cache clearing functionality."""
        # Create test files
        file_configs = [
            {"filename": "anime_ep01_1080p.mkv", "title": "Test Anime", "episode": 1, "quality": "1080p"},
            {"filename": "anime_ep02_1080p.mkv", "title": "Test Anime", "episode": 2, "quality": "1080p"},
        ]

        test_files = self.create_test_files(temp_directories, file_configs)

        # Add files to organizer
        for file in test_files:
            organizer.add_file(file)

        # Verify files are cached
        assert organizer.file_count == 2

        # Clear cache
        organizer.clear_cache()

        # Verify cache is empty
        assert organizer.file_count == 0

        # Try to get files (should return None)
        for file in test_files:
            title = file.metadata.title if file.metadata else "Unknown"
            episode = file.metadata.episode if file.metadata else 0
            result = organizer.get_file(title, episode)
            assert result is None

    def test_scenario_8_performance_under_load(self, organizer, temp_directories):
        """Test scenario: Performance under load with many operations."""
        # Create test files
        file_configs = []
        for i in range(50):
            file_configs.append({
                "filename": f"anime_ep{i+1:02d}_1080p.mkv",
                "title": "Test Anime",
                "episode": i + 1,
                "quality": "1080p",
                "size": 1000000 + i * 1000
            })

        test_files = self.create_test_files(temp_directories, file_configs)

        # Add files to organizer
        for file in test_files:
            organizer.add_file(file)

        # Verify files are cached
        assert organizer.file_count == 50

        # Test multiple operations
        duplicates = organizer.find_duplicates()
        plan = organizer.generate_plan(test_files)
        results = organizer.organize(test_files, dry_run=True)

        # All operations should complete successfully
        assert len(duplicates) == 0
        assert len(plan) == 50
        assert results is not None
        assert len(results) == 50
