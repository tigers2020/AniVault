"""Tests for parallel file processing functionality."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from src.core.parallel_file_processor import (
    ParallelFileProcessor,
    process_single_file_path,
    create_anime_file_only,
    parse_anime_file_only,
    get_processing_statistics
)
from src.core.integrated_parallel_processor import (
    IntegratedParallelProcessor,
    process_files_parallel,
    process_files_with_progress
)
from src.core.models import AnimeFile, ParsedAnimeInfo, ProcessingResult


class TestParallelFileProcessor:
    """Test cases for ParallelFileProcessor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = ParallelFileProcessor()
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create test files
        self.test_files = []
        for i in range(3):
            test_file = self.temp_dir / f"test_anime_{i:02d}_720p.mkv"
            test_file.write_text("test content")
            self.test_files.append(test_file)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_process_single_file_path_success(self):
        """Test successful processing of a single file path."""
        file_path = self.test_files[0]
        
        result = self.processor.process_single_file_path(file_path, include_metadata=True)
        
        assert result.success is True
        assert result.anime_file is not None
        assert result.anime_file.filename == file_path.name
        assert result.anime_file.file_path == file_path
        assert result.processing_time > 0
        assert result.error is None
    
    def test_process_single_file_path_nonexistent(self):
        """Test processing of a non-existent file path."""
        nonexistent_file = self.temp_dir / "nonexistent.mkv"
        
        result = self.processor.process_single_file_path(nonexistent_file)
        
        assert result.success is False
        assert result.anime_file is None
        assert result.error is not None
        assert "Failed to create AnimeFile" in result.error
    
    def test_process_single_file_path_without_metadata(self):
        """Test processing without metadata parsing."""
        file_path = self.test_files[0]
        
        result = self.processor.process_single_file_path(file_path, include_metadata=False)
        
        assert result.success is True
        assert result.anime_file is not None
        assert result.parsed_info is None
    
    def test_process_file_paths_batch(self):
        """Test batch processing of multiple file paths."""
        results = self.processor.process_file_paths_batch(
            self.test_files, include_metadata=True
        )
        
        assert len(results) == 3
        for result in results:
            assert result.success is True
            assert result.anime_file is not None
            assert result.processing_time > 0
    
    def test_create_anime_file_only(self):
        """Test creating AnimeFile object only."""
        file_path = self.test_files[0]
        
        anime_file = self.processor.create_anime_file_only(file_path)
        
        assert anime_file is not None
        assert anime_file.filename == file_path.name
        assert anime_file.file_path == file_path
        assert anime_file.file_size > 0
    
    def test_create_anime_file_only_nonexistent(self):
        """Test creating AnimeFile for non-existent file."""
        nonexistent_file = self.temp_dir / "nonexistent.mkv"
        
        anime_file = self.processor.create_anime_file_only(nonexistent_file)
        
        assert anime_file is None


class TestProcessingFunctions:
    """Test cases for standalone processing functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create test file
        self.test_file = self.temp_dir / "test_anime_01_720p.mkv"
        self.test_file.write_text("test content")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_process_single_file_path_function(self):
        """Test the standalone process_single_file_path function."""
        result = process_single_file_path(self.test_file, include_metadata=True)
        
        assert result.success is True
        assert result.anime_file is not None
        assert result.anime_file.filename == self.test_file.name
    
    def test_create_anime_file_only_function(self):
        """Test the standalone create_anime_file_only function."""
        anime_file = create_anime_file_only(self.test_file)
        
        assert anime_file is not None
        assert anime_file.filename == self.test_file.name
        assert anime_file.file_size > 0
    
    @patch('src.core.parallel_file_processor.AnimeParser')
    def test_parse_anime_file_only_function(self, mock_parser):
        """Test the standalone parse_anime_file_only function."""
        # Create a mock AnimeFile
        anime_file = AnimeFile(
            file_path=self.test_file,
            filename=self.test_file.name,
            file_size=1024,
            file_extension=".mkv",
            created_at=1234567890,
            modified_at=1234567890
        )
        
        # Mock the parser to return a ParsedAnimeInfo
        mock_parsed_info = Mock(spec=ParsedAnimeInfo)
        mock_parser_instance = mock_parser.return_value
        mock_parser_instance.parse_anime_file.return_value = mock_parsed_info
        
        result = parse_anime_file_only(anime_file)
        
        assert result is not None
        mock_parser_instance.parse_anime_file.assert_called_once_with(anime_file)


class TestIntegratedParallelProcessor:
    """Test cases for IntegratedParallelProcessor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create test files
        self.test_files = []
        for i in range(5):
            test_file = self.temp_dir / f"test_anime_{i:02d}_720p.mkv"
            test_file.write_text("test content")
            self.test_files.append(test_file)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_process_files_parallel_direct(self):
        """Test direct parallel processing without queue."""
        processor = IntegratedParallelProcessor(
            max_workers=2,
            executor_type="thread"
        )
        
        results = processor.process_files_parallel(
            self.test_files, include_metadata=True, use_queue=False
        )
        
        assert len(results) == 5
        for result in results:
            assert result.success is True
            assert result.anime_file is not None
    
    def test_process_files_in_batches(self):
        """Test batch processing."""
        processor = IntegratedParallelProcessor(max_workers=2)
        
        results = processor.process_files_in_batches(
            self.test_files, batch_size=2, include_metadata=True
        )
        
        assert len(results) == 5
        for result in results:
            assert result.success is True
            assert result.anime_file is not None
    
    def test_process_files_with_progress(self):
        """Test processing with progress callback."""
        processor = IntegratedParallelProcessor(max_workers=2)
        
        progress_updates = []
        def progress_callback(processed, total, message):
            progress_updates.append((processed, total, message))
        
        results = processor.process_files_with_progress(
            self.test_files, progress_callback, include_metadata=True
        )
        
        assert len(results) == 5
        assert len(progress_updates) > 0
        
        # Check that progress callback was called
        final_update = progress_updates[-1]
        assert final_update[0] == final_update[1]  # processed == total
    
    def test_get_processing_stats(self):
        """Test getting processing statistics."""
        processor = IntegratedParallelProcessor()
        
        # Create some mock results
        results = []
        for i in range(3):
            anime_file = AnimeFile(
                file_path=self.test_files[i],
                filename=self.test_files[i].name,
                file_size=1024,
                file_extension=".mkv",
                created_at=1234567890,
                modified_at=1234567890
            )
            result = ProcessingResult(
                success=True,
                anime_file=anime_file,
                processing_time=0.1
            )
            results.append(result)
        
        stats = processor.get_processing_stats(results)
        
        assert stats["total_files"] == 3
        assert stats["successful_files"] == 3
        assert stats["failed_files"] == 0
        assert stats["success_rate"] == 100.0
        assert stats["avg_processing_time"] > 0
    
    def test_context_manager(self):
        """Test using processor as context manager."""
        with IntegratedParallelProcessor(max_workers=2) as processor:
            results = processor.process_files_parallel(
                self.test_files[:2], include_metadata=True, use_queue=False
            )
            
            assert len(results) == 2
            for result in results:
                assert result.success is True


class TestProcessingStatistics:
    """Test cases for processing statistics functionality."""
    
    def test_get_processing_statistics_empty(self):
        """Test statistics with empty results."""
        stats = get_processing_statistics([])
        
        assert stats["total_files"] == 0
        assert stats["successful_files"] == 0
        assert stats["failed_files"] == 0
        assert stats["success_rate"] == 0
    
    def test_get_processing_statistics_mixed(self):
        """Test statistics with mixed success/failure results."""
        # Create mock results
        results = []
        
        # Successful results
        for i in range(2):
            anime_file = Mock(spec=AnimeFile)
            result = ProcessingResult(
                success=True,
                anime_file=anime_file,
                parsed_info=Mock(spec=ParsedAnimeInfo),
                processing_time=0.1
            )
            results.append(result)
        
        # Failed result
        failed_result = ProcessingResult(
            success=False,
            error="Test error",
            processing_time=0.05
        )
        results.append(failed_result)
        
        stats = get_processing_statistics(results)
        
        assert stats["total_files"] == 3
        assert stats["successful_files"] == 2
        assert stats["failed_files"] == 1
        assert stats["success_rate"] == (2/3) * 100
        assert stats["parsed_files"] == 2
        assert stats["parse_success_rate"] == 100.0
        assert stats["avg_processing_time"] == 0.1
        assert stats["max_processing_time"] == 0.1
        assert stats["min_processing_time"] == 0.1


class TestConvenienceFunctions:
    """Test cases for convenience functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create test files
        self.test_files = []
        for i in range(3):
            test_file = self.temp_dir / f"test_anime_{i:02d}_720p.mkv"
            test_file.write_text("test content")
            self.test_files.append(test_file)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_process_files_parallel_convenience(self):
        """Test the convenience process_files_parallel function."""
        results = process_files_parallel(
            self.test_files, max_workers=2, include_metadata=True
        )
        
        assert len(results) == 3
        for result in results:
            assert result.success is True
            assert result.anime_file is not None
    
    def test_process_files_with_progress_convenience(self):
        """Test the convenience process_files_with_progress function."""
        progress_updates = []
        def progress_callback(processed, total, message):
            progress_updates.append((processed, total, message))
        
        results = process_files_with_progress(
            self.test_files, progress_callback, max_workers=2
        )
        
        assert len(results) == 3
        assert len(progress_updates) > 0


if __name__ == "__main__":
    pytest.main([__file__])
