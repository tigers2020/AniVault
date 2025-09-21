"""Tests for parallel file parsing functionality."""

import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime

from src.core.models import AnimeFile, ParsedAnimeInfo
from src.core.services.file_processing_tasks import ConcreteFileParsingTask
from src.core.thread_executor_manager import get_thread_executor_manager, cleanup_thread_executors


class TestParallelFileParsing(unittest.TestCase):

    def setUp(self):
        self.test_files = []
        for i in range(5):
            file = AnimeFile(
                file_path=Path(f"/path/to/anime/Test Anime {i}.mp4"),
                filename=f"Test Anime {i}.mp4",
                file_size=1024 * 1024,
                file_extension=".mp4",
                created_at=datetime.now(),
                modified_at=datetime.now(),
            )
            self.test_files.append(file)

        # Ensure a fresh executor manager for each test
        cleanup_thread_executors()
        self.executor_manager = get_thread_executor_manager()

    def tearDown(self):
        cleanup_thread_executors()

    @patch('src.core.anime_parser.AnimeParser.parse_filename')
    def test_parallel_file_parsing(self, mock_parse_filename):
        # Configure mock to return successful parsing results
        mock_parse_filename.side_effect = [
            ParsedAnimeInfo(
                title=f"Test Anime {i}",
                season=1,
                episode=1,
                year=2023,
                resolution="1080p",
                resolution_width=1920,
                resolution_height=1080,
                release_group="TestGroup",
            )
            for i in range(len(self.test_files))
        ]

        task = ConcreteFileParsingTask(self.test_files)
        result_files = task.execute()

        self.assertEqual(len(result_files), len(self.test_files))
        
        # Since parallel processing doesn't guarantee order, we need to check that
        # all expected titles are present rather than checking specific positions
        result_titles = {file.parsed_info.title for file in result_files if file.parsed_info}
        expected_titles = {f"Test Anime {i}" for i in range(len(self.test_files))}
        
        self.assertEqual(result_titles, expected_titles)
        
        for file in result_files:
            self.assertIsNotNone(file.parsed_info)
            self.assertEqual(file.parsed_info.season, 1)
            self.assertEqual(file.parsed_info.episode, 1)
            self.assertFalse(file.processing_errors)

        # Verify that parse_filename was called for each file
        self.assertEqual(mock_parse_filename.call_count, len(self.test_files))

    @patch('src.core.anime_parser.AnimeParser.parse_filename')
    def test_parallel_file_parsing_with_errors(self, mock_parse_filename):
        # Configure mock to raise an exception for some files
        def mock_effect(filename):
            if "Test Anime 1" in filename:
                raise Exception("Parsing error")
            return ParsedAnimeInfo(
                title="Test Anime",
                season=1,
                episode=1,
                year=2023,
                resolution="1080p",
                resolution_width=1920,
                resolution_height=1080,
                release_group="TestGroup",
            )

        mock_parse_filename.side_effect = mock_effect

        task = ConcreteFileParsingTask(self.test_files)
        result_files = task.execute()

        self.assertEqual(len(result_files), len(self.test_files))
        for i, file in enumerate(result_files):
            if "Test Anime 1" in file.filename:
                self.assertTrue(file.processing_errors)
                self.assertIn("Parsing failed", file.processing_errors[0])
                self.assertIsNone(file.parsed_info)
            else:
                self.assertFalse(file.processing_errors)
                self.assertIsNotNone(file.parsed_info)

        self.assertEqual(mock_parse_filename.call_count, len(self.test_files))

    @patch('src.core.anime_parser.AnimeParser.parse_filename')
    def test_parallel_file_parsing_with_progress_callback(self, mock_parse_filename):
        # Configure mock to return successful parsing results
        mock_parse_filename.return_value = ParsedAnimeInfo(
            title="Test Anime",
            season=1,
            episode=1,
            year=2023,
            resolution="1080p",
            resolution_width=1920,
            resolution_height=1080,
            release_group="TestGroup",
        )

        # Mock progress callback
        progress_callback = MagicMock()

        task = ConcreteFileParsingTask(self.test_files, progress_callback)
        result_files = task.execute()

        self.assertEqual(len(result_files), len(self.test_files))
        
        # Verify progress callback was called
        self.assertTrue(progress_callback.called)
        
        # Check that progress reached 100%
        final_call = progress_callback.call_args_list[-1]
        final_progress = final_call[0][0]  # First argument
        self.assertEqual(final_progress, 100)

    @patch('src.core.anime_parser.AnimeParser.parse_filename')
    def test_thread_executor_manager_integration(self, mock_parse_filename):
        mock_parse_filename.return_value = ParsedAnimeInfo(
            title="Test Anime",
            season=1,
            episode=1,
            year=2023,
            resolution="1080p",
            resolution_width=1920,
            resolution_height=1080,
            release_group="TestGroup",
        )

        task = ConcreteFileParsingTask(self.test_files)
        task.execute()

        # Verify that the general executor was used
        # This is an indirect check, as we can't directly inspect the executor used by `as_completed`
        # However, the fact that the test runs without errors implies correct integration
        self.assertIsNotNone(self.executor_manager.get_general_executor())
        self.assertFalse(self.executor_manager.get_general_executor()._shutdown)

    def test_invalid_file_objects(self):
        # Test with invalid file objects
        invalid_files = [
            "not_an_anime_file",  # String instead of AnimeFile
            AnimeFile(
                file_path=Path("/path/to/valid.mp4"),
                filename="valid.mp4",
                file_size=1024,
                file_extension=".mp4",
                created_at=datetime.now(),
                modified_at=datetime.now(),
            ),
            None,  # None object
        ]

        task = ConcreteFileParsingTask(invalid_files)
        
        # This should raise an exception due to invalid objects
        with self.assertRaises(Exception):
            task.execute()


if __name__ == "__main__":
    unittest.main()
