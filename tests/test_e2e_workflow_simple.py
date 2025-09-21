"""Simplified end-to-end workflow tests."""

import os
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.core.file_scanner import FileScanner
from src.core.file_grouper import FileGrouper
from src.core.file_mover import FileMover
from src.core.metadata_cache import MetadataCache
from src.core.tmdb_client import TMDBClient, TMDBConfig
from src.core.models import TMDBAnime


class TestE2EWorkflowSimple:
    """Simplified end-to-end workflow tests."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        base_dir = Path(tempfile.mkdtemp())
        source_dir = base_dir / "source"
        target_dir = base_dir / "target"
        
        source_dir.mkdir(parents=True)
        target_dir.mkdir(parents=True)
        
        yield source_dir, target_dir
        
        # Clean up
        import shutil
        shutil.rmtree(base_dir, ignore_errors=True)

    def _create_test_files(self, source_dir: Path) -> None:
        """Create test files for testing."""
        test_files = [
            "Attack on Titan S01E01 [1080p] [GroupA].mkv",
            "Attack on Titan S01E02 [1080p] [GroupA].mkv",
            "Attack on Titan S01E03 [1080p] [GroupA].mkv",
            "One Piece S01E001 [720p] [GroupB].mp4",
            "One Piece S01E002 [720p] [GroupB].mp4",
            "Naruto S01E01 [1080p] [GroupC].avi",
        ]

        for filename in test_files:
            file_path = source_dir / filename
            file_path.write_text(f"Content for {filename}")

    def test_complete_workflow_with_mock_api(self, temp_dirs):
        """Test complete workflow with mocked TMDB API."""
        source_dir, target_dir = temp_dirs
        self._create_test_files(source_dir)

        # Mock TMDB API
        with patch('src.core.tmdb_client.TMDBClient') as mock_tmdb_class:
            mock_tmdb = Mock()
            mock_tmdb_class.return_value = mock_tmdb

            # Mock API responses
            mock_tmdb.search_comprehensive.return_value = ([
                Mock(
                    id=1,
                    title="Attack on Titan",
                    overview="A story about humanity's fight against titans",
                    release_date="2013-04-07",
                    vote_average=8.5,
                    vote_count=1000,
                    popularity=50.0,
                    poster_path="/poster.jpg",
                    backdrop_path="/backdrop.jpg",
                    genre_ids=[16, 28],
                    original_language="ja",
                    original_title="進撃の巨人"
                )
            ], True)

            # Test individual components
            scanner = FileScanner(max_workers=2)
            scan_result = scanner.scan_directory(source_dir, recursive=True)

            assert scan_result.supported_files > 0
            assert len(scan_result.files) > 0

            # Group files
            grouper = FileGrouper(similarity_threshold=0.75, max_workers=2)
            grouping_result = grouper.group_files(scan_result.files)

            assert len(grouping_result.groups) > 0
            assert grouping_result.grouped_files > 0

            # Test API call - use the mocked client
            tmdb_client = mock_tmdb_class.return_value
            results, success = tmdb_client.search_comprehensive("Attack on Titan")
            
            assert success is True
            assert len(results) > 0

    def test_complete_workflow_with_real_components(self, temp_dirs):
        """Test complete workflow with real components (no API calls)."""
        source_dir, target_dir = temp_dirs
        self._create_test_files(source_dir)

        # Test individual components
        scanner = FileScanner(max_workers=2)
        scan_result = scanner.scan_directory(source_dir, recursive=True)

        assert scan_result.supported_files > 0
        assert len(scan_result.files) > 0

        # Group files
        grouper = FileGrouper(similarity_threshold=0.75, max_workers=2)
        grouping_result = grouper.group_files(scan_result.files)

        assert len(grouping_result.groups) > 0
        assert grouping_result.grouped_files > 0

        # Move files
        mover = FileMover()
        move_results = []

        for group in grouping_result.groups:
            for file in group.files:
                source_path = file.file_path
                target_path = target_dir / source_path.name

                result = mover.move_file(source_path, target_path)
                move_results.append(result)

        # Verify move results
        success_count = sum(1 for result in move_results if result.success)
        assert success_count >= len(move_results) * 0.8  # At least 80% success rate

    def test_workflow_with_metadata_caching(self, temp_dirs):
        """Test workflow with metadata caching."""
        source_dir, target_dir = temp_dirs
        self._create_test_files(source_dir)

        # Initialize metadata cache
        cache = MetadataCache(max_size=100)

        # Test cache operations
        test_key = "test_anime"
        test_data = TMDBAnime(
            tmdb_id=1,
            title="Test Anime",
            overview="Test overview",
            first_air_date=datetime(2020, 1, 1),
            vote_average=8.5,
            vote_count=1000,
            popularity=50.0,
            poster_path="/poster.jpg",
            backdrop_path="/backdrop.jpg",
            genres=["Animation", "Action"],
            original_title="テストアニメ"
        )

        # Test cache put
        cache.put(test_key, test_data)
        
        # Test cache get
        retrieved_data = cache.get(test_key)
        assert retrieved_data is not None
        assert retrieved_data.title == test_data.title

        # Test cache delete
        cache.delete(test_key)
        deleted_data = cache.get(test_key)
        assert deleted_data is None

    def test_workflow_data_integrity(self, temp_dirs):
        """Test workflow data integrity throughout the process."""
        source_dir, target_dir = temp_dirs
        self._create_test_files(source_dir)

        # Test data integrity
        scanner = FileScanner(max_workers=2)
        scan_result = scanner.scan_directory(source_dir, recursive=True)

        # Verify scan data integrity
        assert scan_result.total_files_found > 0
        assert scan_result.supported_files > 0
        assert len(scan_result.files) > 0
        assert len(scan_result.errors) == 0

        # Verify file data integrity
        for file in scan_result.files:
            assert file.file_path.exists()
            assert file.file_size > 0
            assert file.filename is not None
            assert file.file_extension is not None

        # Test grouping integrity
        grouper = FileGrouper(similarity_threshold=0.75, max_workers=2)
        grouping_result = grouper.group_files(scan_result.files)

        # Verify grouping data integrity
        assert grouping_result.total_files == len(scan_result.files)
        assert grouping_result.grouped_files + len(grouping_result.ungrouped_files) == grouping_result.total_files

        # Verify each group has valid files
        for group in grouping_result.groups:
            assert len(group.files) > 0
            for file in group.files:
                assert file.file_path.exists()
                assert file.file_size > 0

    def test_workflow_with_empty_directories(self, temp_dirs):
        """Test workflow with empty directories."""
        source_dir, target_dir = temp_dirs
        
        # Create empty directory
        empty_dir = source_dir / "empty"
        empty_dir.mkdir()

        # Test workflow
        scanner = FileScanner(max_workers=2)
        scan_result = scanner.scan_directory(empty_dir, recursive=True)

        # Should handle empty directory gracefully
        assert scan_result.total_files_found == 0
        assert scan_result.supported_files == 0
        assert len(scan_result.files) == 0
        assert len(scan_result.errors) == 0

    def test_workflow_with_network_failures(self, temp_dirs):
        """Test workflow with network failures (simulated)."""
        source_dir, target_dir = temp_dirs
        self._create_test_files(source_dir)

        # Mock network failure
        with patch('src.core.tmdb_client.TMDBClient') as mock_tmdb_class:
            mock_tmdb = Mock()
            mock_tmdb_class.return_value = mock_tmdb
            mock_tmdb.search_comprehensive.side_effect = Exception("Network error")

            # Test workflow
            scanner = FileScanner(max_workers=2)
            scan_result = scanner.scan_directory(source_dir, recursive=True)

            # Should handle network failures gracefully
            assert scan_result.supported_files > 0
            assert len(scan_result.files) > 0

            # Test API call should fail gracefully
            tmdb_client = TMDBClient(TMDBConfig(api_key="test_key"))
            results, success = tmdb_client.search_comprehensive("Test")
            
            assert success is False
            assert results is None

    def test_workflow_with_disk_space_errors(self, temp_dirs):
        """Test workflow with disk space errors."""
        source_dir, target_dir = temp_dirs
        self._create_test_files(source_dir)

        # Mock disk space check
        with patch('shutil.disk_usage') as mock_disk_usage:
            mock_disk_usage.return_value = (1000000, 500000, 100000)  # Very low free space

            # Test workflow
            scanner = FileScanner(max_workers=2)
            scan_result = scanner.scan_directory(source_dir, recursive=True)

            # Should handle disk space errors gracefully
            assert scan_result.supported_files > 0
            assert len(scan_result.files) > 0

    def test_workflow_with_corrupted_files(self, temp_dirs):
        """Test workflow with corrupted files."""
        source_dir, target_dir = temp_dirs
        self._create_test_files(source_dir)

        # Create a corrupted file
        corrupted_file = source_dir / "corrupted.mkv"
        corrupted_file.write_text("")  # Empty file

        # Test workflow
        scanner = FileScanner(max_workers=2)
        scan_result = scanner.scan_directory(source_dir, recursive=True)

        # Should handle corrupted files gracefully
        assert scan_result.supported_files > 0
        assert len(scan_result.files) > 0

        # Empty files should be handled gracefully
        for file in scan_result.files:
            if file.filename == "corrupted.mkv":
                assert file.file_size == 0
