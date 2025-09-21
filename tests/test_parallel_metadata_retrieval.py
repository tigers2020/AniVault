"""Test parallel metadata retrieval functionality."""

import unittest
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor

from src.core.models import AnimeFile, ParsedAnimeInfo
from src.core.services.file_processing_tasks import ConcreteMetadataRetrievalTask
from src.core.thread_executor_manager import get_thread_executor_manager


class TestParallelMetadataRetrieval(unittest.TestCase):
    """Test parallel metadata retrieval functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create test files with parsed info
        self.test_files = []
        for i in range(5):
            file = AnimeFile(
                file_path=f"/test/anime_{i}.mp4",
                filename=f"Anime_{i}_Episode_01.mp4",
                file_size=1024 * 1024,
                file_extension=".mp4",
                created_at=None,
                modified_at=None,
            )
            file.parsed_info = ParsedAnimeInfo(
                title=f"Test Anime {i}",
                season=1,
                episode=1,
                year=2023,
                resolution="1080p",
                resolution_width=1920,
                resolution_height=1080,
                release_group="TestGroup",
            )
            self.test_files.append(file)

        # Mock TMDB API key
        self.api_key = "test_api_key"

    def tearDown(self):
        """Clean up after tests."""
        # Clean up thread executors
        manager = get_thread_executor_manager()
        manager.shutdown_all(wait=True)

    @patch('src.core.services.file_processing_tasks.TMDBClient')
    def test_parallel_metadata_retrieval(self, mock_tmdb_client_class):
        """Test that metadata retrieval uses parallel processing."""
        # Mock TMDB client
        mock_tmdb_client = Mock()
        mock_tmdb_client_class.return_value = mock_tmdb_client
        
        # Mock search results
        mock_tmdb_client.search_tv_series.return_value = [{
            "id": 12345,
            "name": "Test Anime",
            "original_name": "Test Anime",
            "overview": "A test anime",
            "first_air_date": "2023-01-01",
            "poster_path": "/test_poster.jpg",
            "backdrop_path": "/test_backdrop.jpg",
            "vote_average": 8.5,
            "vote_count": 100,
            "popularity": 75.0,
        }]

        # Create task
        task = ConcreteMetadataRetrievalTask(self.test_files, self.api_key)
        
        # Execute task
        result = task.execute()
        
        # Verify results
        self.assertEqual(len(result), 5)
        
        # Verify that all files have metadata
        for file in result:
            self.assertIsNotNone(file.tmdb_info)
            self.assertEqual(file.tmdb_info.tmdb_id, 12345)
            self.assertEqual(file.tmdb_info.title, "Test Anime")
        
        # Verify that TMDB client was called for each file
        self.assertEqual(mock_tmdb_client.search_tv_series.call_count, 5)

    @patch('src.core.services.file_processing_tasks.TMDBClient')
    def test_parallel_metadata_retrieval_with_errors(self, mock_tmdb_client_class):
        """Test parallel metadata retrieval with some files failing."""
        # Mock TMDB client
        mock_tmdb_client = Mock()
        mock_tmdb_client_class.return_value = mock_tmdb_client
        
        # Mock search results - some succeed, some fail
        def mock_search(title):
            if "Anime 0" in title or "Anime 1" in title:
                return [{
                    "id": 12345,
                    "name": "Test Anime",
                    "original_name": "Test Anime",
                    "overview": "A test anime",
                    "first_air_date": "2023-01-01",
                    "poster_path": "/test_poster.jpg",
                    "backdrop_path": "/test_backdrop.jpg",
                    "vote_average": 8.5,
                    "vote_count": 100,
                    "popularity": 75.0,
                }]
            else:
                raise Exception("TMDB API error")
        
        mock_tmdb_client.search_tv_series.side_effect = mock_search

        # Create task
        task = ConcreteMetadataRetrievalTask(self.test_files, self.api_key)
        
        # Execute task
        result = task.execute()
        
        # Verify results
        self.assertEqual(len(result), 5)
        
        # Verify that some files have metadata and some have errors
        success_count = 0
        error_count = 0
        
        for file in result:
            if file.tmdb_info is not None:
                success_count += 1
                self.assertEqual(file.tmdb_info.tmdb_id, 12345)
            elif file.processing_errors:
                error_count += 1
                self.assertTrue(any("Metadata retrieval failed" in error for error in file.processing_errors))
        
        # Should have 2 successes and 3 errors
        self.assertEqual(success_count, 2)
        self.assertEqual(error_count, 3)

    def test_thread_executor_manager_integration(self):
        """Test that the task integrates correctly with ThreadExecutorManager."""
        # Get the thread executor manager
        manager = get_thread_executor_manager()
        
        # Verify it has the expected methods
        self.assertTrue(hasattr(manager, 'get_tmdb_executor'))
        self.assertTrue(hasattr(manager, 'get_file_scan_executor'))
        self.assertTrue(hasattr(manager, 'get_general_executor'))
        
        # Test that executors are created correctly
        tmdb_executor = manager.get_tmdb_executor()
        self.assertIsInstance(tmdb_executor, ThreadPoolExecutor)
        
        # Verify executor configuration
        config = manager.get_configuration_info()
        self.assertIn('tmdb_max_workers', config)
        self.assertIn('file_scan_max_workers', config)
        self.assertIn('general_max_workers', config)
        
        # Verify reasonable worker counts
        self.assertGreater(config['tmdb_max_workers'], 0)
        self.assertLessEqual(config['tmdb_max_workers'], 100)  # Reasonable upper bound


if __name__ == '__main__':
    unittest.main()
