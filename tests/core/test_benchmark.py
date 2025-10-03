"""
Tests for the benchmark module.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from anivault.core.benchmark import (
    BenchmarkResult,
    BenchmarkRunner,
    BenchmarkSummary,
    GroundTruthEntry,
)
from anivault.core.statistics import StatisticsCollector


class TestGroundTruthEntry:
    """Test GroundTruthEntry dataclass."""

    def test_ground_truth_entry_creation(self):
        """Test creating a GroundTruthEntry."""
        entry = GroundTruthEntry(
            filename="test.mkv",
            anitopy_result={"anime_title": "Test Anime"},
            expected_tmdb_id=123,
            expected_title="Test Anime",
            expected_media_type="tv",
        )

        assert entry.filename == "test.mkv"
        assert entry.expected_tmdb_id == 123
        assert entry.confidence_threshold == 0.7  # default value
        assert entry.notes is None


class TestBenchmarkResult:
    """Test BenchmarkResult dataclass."""

    def test_benchmark_result_creation(self):
        """Test creating a BenchmarkResult."""
        result = BenchmarkResult(
            filename="test.mkv",
            expected_tmdb_id=123,
            actual_tmdb_id=123,
            expected_title="Test Anime",
            actual_title="Test Anime",
            confidence_score=0.9,
            is_correct=True,
            processing_time=1.5,
        )

        assert result.filename == "test.mkv"
        assert result.is_correct is True
        assert result.confidence_score == 0.9


class TestBenchmarkSummary:
    """Test BenchmarkSummary dataclass."""

    def test_benchmark_summary_creation(self):
        """Test creating a BenchmarkSummary."""
        summary = BenchmarkSummary(
            total_tests=10,
            correct_matches=8,
            incorrect_matches=1,
            failed_matches=1,
            accuracy=80.0,
            average_confidence=0.85,
            average_processing_time=1.2,
            total_processing_time=12.0,
            cache_hit_ratio=75.0,
            api_calls=5,
            api_errors=0,
            timestamp="2023-01-01T00:00:00Z",
        )

        assert summary.total_tests == 10
        assert summary.accuracy == 80.0
        assert summary.cache_hit_ratio == 75.0


class TestBenchmarkRunner:
    """Test BenchmarkRunner class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def mock_tmdb_client(self):
        """Create a mock TMDB client."""
        client = MagicMock()
        client.search_media = AsyncMock(
            return_value=[{"id": 123, "title": "Test Anime", "media_type": "tv"}]
        )
        return client

    @pytest.fixture
    def benchmark_runner(self, temp_dir, mock_tmdb_client):
        """Create a BenchmarkRunner instance for testing."""
        with patch("anivault.core.benchmark.TMDBClient", return_value=mock_tmdb_client):
            runner = BenchmarkRunner(
                cache_dir=temp_dir,
                tmdb_api_key="test_key",  # pragma: allowlist secret
                statistics=StatisticsCollector(),
            )
            return runner

    def test_initialization(self, temp_dir, mock_tmdb_client):
        """Test BenchmarkRunner initialization."""
        with patch("anivault.core.benchmark.TMDBClient", return_value=mock_tmdb_client):
            runner = BenchmarkRunner(cache_dir=temp_dir, tmdb_api_key="test_key")

            assert runner.cache_dir == temp_dir
            assert runner.tmdb_api_key == "test_key"
            assert isinstance(runner.statistics, StatisticsCollector)
            assert len(runner.ground_truth) == 0

    def test_create_sample_dataset(self, benchmark_runner, temp_dir):
        """Test creating a sample dataset."""
        output_path = temp_dir / "sample_dataset.json"

        benchmark_runner.create_sample_dataset(output_path)

        assert output_path.exists()

        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)

        assert "metadata" in data
        assert "entries" in data
        assert len(data["entries"]) == 5
        assert data["metadata"]["total_entries"] == 5

    def test_load_ground_truth(self, benchmark_runner, temp_dir):
        """Test loading ground truth dataset."""
        # Create a test dataset
        test_data = {
            "metadata": {
                "created_at": "2023-01-01T00:00:00Z",
                "version": "1.0",
                "description": "Test dataset",
                "total_entries": 2,
            },
            "entries": [
                {
                    "filename": "test1.mkv",
                    "anitopy_result": {"anime_title": "Test Anime 1"},
                    "expected_tmdb_id": 123,
                    "expected_title": "Test Anime 1",
                    "expected_media_type": "tv",
                    "confidence_threshold": 0.8,
                },
                {
                    "filename": "test2.mkv",
                    "anitopy_result": {"anime_title": "Test Anime 2"},
                    "expected_tmdb_id": 456,
                    "expected_title": "Test Anime 2",
                    "expected_media_type": "movie",
                    "confidence_threshold": 0.9,
                },
            ],
        }

        dataset_path = temp_dir / "test_dataset.json"
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        benchmark_runner.load_ground_truth(dataset_path)

        assert len(benchmark_runner.ground_truth) == 2
        assert benchmark_runner.ground_truth[0].filename == "test1.mkv"
        assert benchmark_runner.ground_truth[1].expected_tmdb_id == 456

    def test_load_ground_truth_file_not_found(self, benchmark_runner, temp_dir):
        """Test loading ground truth with non-existent file."""
        dataset_path = temp_dir / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            benchmark_runner.load_ground_truth(dataset_path)

    @pytest.mark.asyncio
    async def test_run_benchmark_no_dataset(self, benchmark_runner):
        """Test running benchmark without loaded dataset."""
        with pytest.raises(ValueError, match="No ground truth dataset loaded"):
            await benchmark_runner.run_benchmark()

    @pytest.mark.asyncio
    async def test_run_benchmark_success(self, benchmark_runner):
        """Test running benchmark with successful matches."""
        # Load sample dataset
        benchmark_runner.ground_truth = [
            GroundTruthEntry(
                filename="test1.mkv",
                anitopy_result={"anime_title": "Test Anime 1"},
                expected_tmdb_id=123,
                expected_title="Test Anime 1",
                expected_media_type="tv",
            )
        ]

        # Mock the matching engine to return a successful match
        mock_result = {"id": 123, "title": "Test Anime 1", "confidence_score": 0.9}
        benchmark_runner.matching_engine.find_match = AsyncMock(
            return_value=mock_result
        )

        results, summary = await benchmark_runner.run_benchmark()

        assert len(results) == 1
        assert results[0].is_correct is True
        assert results[0].actual_tmdb_id == 123
        assert summary.total_tests == 1
        assert summary.correct_matches == 1
        assert summary.accuracy == 100.0

    @pytest.mark.asyncio
    async def test_run_benchmark_no_match(self, benchmark_runner):
        """Test running benchmark with no match found."""
        # Load sample dataset
        benchmark_runner.ground_truth = [
            GroundTruthEntry(
                filename="test1.mkv",
                anitopy_result={"anime_title": "Test Anime 1"},
                expected_tmdb_id=123,
                expected_title="Test Anime 1",
                expected_media_type="tv",
            )
        ]

        # Mock the matching engine to return no match
        benchmark_runner.matching_engine.find_match = AsyncMock(return_value=None)

        results, summary = await benchmark_runner.run_benchmark()

        assert len(results) == 1
        assert results[0].is_correct is False
        assert results[0].actual_tmdb_id is None
        assert results[0].error_message == "No match found"
        assert summary.failed_matches == 1

    @pytest.mark.asyncio
    async def test_run_benchmark_incorrect_match(self, benchmark_runner):
        """Test running benchmark with incorrect match."""
        # Load sample dataset
        benchmark_runner.ground_truth = [
            GroundTruthEntry(
                filename="test1.mkv",
                anitopy_result={"anime_title": "Test Anime 1"},
                expected_tmdb_id=123,
                expected_title="Test Anime 1",
                expected_media_type="tv",
            )
        ]

        # Mock the matching engine to return incorrect match
        mock_result = {
            "id": 456,  # Wrong ID
            "title": "Wrong Anime",
            "confidence_score": 0.9,
        }
        benchmark_runner.matching_engine.find_match = AsyncMock(
            return_value=mock_result
        )

        results, summary = await benchmark_runner.run_benchmark()

        assert len(results) == 1
        assert results[0].is_correct is False
        assert results[0].actual_tmdb_id == 456
        assert summary.incorrect_matches == 1

    @pytest.mark.asyncio
    async def test_run_benchmark_exception(self, benchmark_runner):
        """Test running benchmark with exception during processing."""
        # Load sample dataset
        benchmark_runner.ground_truth = [
            GroundTruthEntry(
                filename="test1.mkv",
                anitopy_result={"anime_title": "Test Anime 1"},
                expected_tmdb_id=123,
                expected_title="Test Anime 1",
                expected_media_type="tv",
            )
        ]

        # Mock the matching engine to raise an exception
        benchmark_runner.matching_engine.find_match = AsyncMock(
            side_effect=Exception("Test error")
        )

        results, summary = await benchmark_runner.run_benchmark()

        assert len(results) == 1
        assert results[0].is_correct is False
        assert results[0].error_message == "Test error"
        assert summary.failed_matches == 1

    def test_save_results(self, benchmark_runner, temp_dir):
        """Test saving benchmark results."""
        # Create test results
        results = [
            BenchmarkResult(
                filename="test1.mkv",
                expected_tmdb_id=123,
                actual_tmdb_id=123,
                expected_title="Test Anime 1",
                actual_title="Test Anime 1",
                confidence_score=0.9,
                is_correct=True,
                processing_time=1.5,
            )
        ]

        summary = BenchmarkSummary(
            total_tests=1,
            correct_matches=1,
            incorrect_matches=0,
            failed_matches=0,
            accuracy=100.0,
            average_confidence=0.9,
            average_processing_time=1.5,
            total_processing_time=1.5,
            cache_hit_ratio=0.0,
            api_calls=1,
            api_errors=0,
            timestamp="2023-01-01T00:00:00Z",
        )

        output_path = temp_dir / "results.json"
        benchmark_runner.save_results(results, summary, output_path)

        assert output_path.exists()

        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)

        assert "summary" in data
        assert "results" in data
        assert "statistics" in data
        assert data["summary"]["total_tests"] == 1
        assert len(data["results"]) == 1

    def test_print_summary(self, benchmark_runner, capsys):
        """Test printing benchmark summary."""
        summary = BenchmarkSummary(
            total_tests=10,
            correct_matches=8,
            incorrect_matches=1,
            failed_matches=1,
            accuracy=80.0,
            average_confidence=0.85,
            average_processing_time=1.2,
            total_processing_time=12.0,
            cache_hit_ratio=75.0,
            api_calls=5,
            api_errors=0,
            timestamp="2023-01-01T00:00:00Z",
        )

        benchmark_runner.print_summary(summary)

        captured = capsys.readouterr()
        assert "BENCHMARK RESULTS SUMMARY" in captured.out
        assert "Total Tests:           10" in captured.out
        assert "Accuracy:              80.0%" in captured.out
        assert "Cache Hit Ratio:       75.0%" in captured.out
