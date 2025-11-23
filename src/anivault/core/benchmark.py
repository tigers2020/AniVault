"""
Benchmark Runner and Ground Truth Dataset Module

This module provides comprehensive benchmarking capabilities for the AniVault
matching system, including ground truth dataset management and performance
evaluation against known anime titles.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from anivault.core.matching.engine import MatchingEngine
from anivault.core.statistics import StatisticsCollector
from anivault.shared.constants import (
    CLIFormatting,
    ConfidenceThresholds,
    Encoding,
    JsonKeys,
)
from anivault.shared.protocols.services import TMDBClientProtocol

logger = logging.getLogger(__name__)


@dataclass
class GroundTruthEntry:
    """A single entry in the ground truth dataset.

    Attributes:
        filename: Original filename that was parsed
        anitopy_result: Result from anitopy.parse()
        expected_tmdb_id: Expected TMDB ID for the match
        expected_title: Expected TMDB title for the match
        expected_media_type: Expected media type (tv/movie)
        confidence_threshold: Minimum confidence score for valid match
        notes: Optional notes about this test case
    """

    filename: str
    anitopy_result: dict[str, Any]
    expected_tmdb_id: int
    expected_title: str
    expected_media_type: str
    confidence_threshold: float = ConfidenceThresholds.BENCHMARK_DEFAULT
    notes: str | None = None


@dataclass
class BenchmarkResult:
    """Result of a single benchmark test.

    Attributes:
        filename: Original filename tested
        expected_tmdb_id: Expected TMDB ID
        actual_tmdb_id: Actual TMDB ID found
        expected_title: Expected TMDB title
        actual_title: Actual TMDB title found
        confidence_score: Confidence score of the match
        is_correct: Whether the match was correct
        processing_time: Time taken to process this entry
        error_message: Error message if processing failed
    """

    filename: str
    expected_tmdb_id: int
    actual_tmdb_id: int | None
    expected_title: str
    actual_title: str | None
    confidence_score: float | None
    is_correct: bool
    processing_time: float
    error_message: str | None = None


@dataclass
class BenchmarkSummary:
    """Summary of benchmark results.

    Attributes:
        total_tests: Total number of tests run
        correct_matches: Number of correct matches
        incorrect_matches: Number of incorrect matches
        failed_matches: Number of failed matches
        accuracy: Overall accuracy percentage
        average_confidence: Average confidence score
        average_processing_time: Average processing time per test
        total_processing_time: Total processing time
        cache_hit_ratio: Cache hit ratio during benchmark
        api_calls: Number of API calls made
        api_errors: Number of API errors
    """

    total_tests: int
    correct_matches: int
    incorrect_matches: int
    failed_matches: int
    accuracy: float
    average_confidence: float
    average_processing_time: float
    total_processing_time: float
    cache_hit_ratio: float
    api_calls: int
    api_errors: int
    timestamp: str


class BenchmarkRunner:
    """Benchmark runner for testing matching accuracy and performance.

    This class provides comprehensive benchmarking capabilities including
    ground truth dataset management, performance evaluation, and detailed
    reporting of matching system performance.
    """

    def __init__(
        self,
        cache_dir: Path | str,
        tmdb_api_key: str,
        statistics: StatisticsCollector | None = None,
    ):
        """Initialize the benchmark runner.

        Args:
            cache_dir: Directory for cache storage
            tmdb_api_key: TMDB API key for testing
            statistics: Optional statistics collector for performance tracking
        """
        self.cache_dir = Path(cache_dir)
        self.tmdb_api_key = tmdb_api_key
        self.statistics = statistics or StatisticsCollector()

        # Initialize components (SQLite cache)
        # Import at runtime to avoid dependency layer violation
        # pylint: disable=import-outside-toplevel
        from anivault.core.matching.services import SQLiteCacheAdapter  # noqa: PLC0415
        from anivault.services.cache import SQLiteCacheDB  # noqa: PLC0415
        from anivault.services.tmdb import TMDBClient  # noqa: PLC0415

        cache_db_path = Path(self.cache_dir) / "benchmark_cache.db"
        cache_db = SQLiteCacheDB(cache_db_path, self.statistics)
        cache_adapter = SQLiteCacheAdapter(backend=cache_db, language="ko-KR")
        self.tmdb_client: TMDBClientProtocol = TMDBClient(
            rate_limiter=None,
            semaphore_manager=None,
            state_machine=None,
        )
        self.matching_engine = MatchingEngine(
            cache_adapter=cache_adapter,
            tmdb_client=self.tmdb_client,
            statistics=self.statistics,
        )

        # Ground truth dataset
        self.ground_truth: list[GroundTruthEntry] = []

        logger.info("Initialized BenchmarkRunner with cache_dir=%s", self.cache_dir)

    def load_ground_truth(self, dataset_path: Path | str) -> None:
        """Load ground truth dataset from JSON file.

        Args:
            dataset_path: Path to the ground truth dataset JSON file
        """
        dataset_path = Path(dataset_path)

        if not dataset_path.exists():
            msg = f"Ground truth dataset not found: {dataset_path}"
            raise FileNotFoundError(msg)

        with open(dataset_path, encoding=Encoding.DEFAULT) as f:
            data = json.load(f)

        self.ground_truth = [
            GroundTruthEntry(**entry) for entry in data.get(JsonKeys.ENTRIES, [])
        ]

        logger.info(
            "Loaded %d ground truth entries from %s",
            len(self.ground_truth),
            dataset_path,
        )

    def create_sample_dataset(self, output_path: Path | str) -> None:
        """Create a sample ground truth dataset for testing.

        Args:
            output_path: Path where to save the sample dataset
        """
        sample_entries = [
            GroundTruthEntry(
                filename="Attack.on.Titan.S01E01.1080p.BluRay.x264-GROUP.mkv",
                anitopy_result={
                    "anime_title": "Attack on Titan",
                    "episode_number": "01",
                    "season": "1",
                    "year": 2013,
                    "video_resolution": "1080p",
                    "video_term": "BluRay",
                    "file_extension": "mkv",
                },
                expected_tmdb_id=1399,
                expected_title="Attack on Titan",
                expected_media_type="tv",
                confidence_threshold=ConfidenceThresholds.BENCHMARK_MEDIUM,
                notes="Popular anime series",
            ),
            GroundTruthEntry(
                filename="Spirited.Away.2001.1080p.BluRay.x264-GROUP.mkv",
                anitopy_result={
                    "anime_title": "Spirited Away",
                    "year": 2001,
                    "video_resolution": "1080p",
                    "video_term": "BluRay",
                    "file_extension": "mkv",
                },
                expected_tmdb_id=129,
                expected_title="Spirited Away",
                expected_media_type="movie",
                confidence_threshold=ConfidenceThresholds.BENCHMARK_HIGH,
                notes="Studio Ghibli masterpiece",
            ),
            GroundTruthEntry(
                filename="My.Neighbor.Totoro.1988.1080p.BluRay.x264-GROUP.mkv",
                anitopy_result={
                    "anime_title": "My Neighbor Totoro",
                    "year": 1988,
                    "video_resolution": "1080p",
                    "video_term": "BluRay",
                    "file_extension": "mkv",
                },
                expected_tmdb_id=8392,
                expected_title="My Neighbor Totoro",
                expected_media_type="movie",
                confidence_threshold=ConfidenceThresholds.BENCHMARK_HIGH,
                notes="Classic Studio Ghibli film",
            ),
            GroundTruthEntry(
                filename="One.Piece.S01E001.1080p.WEB-DL.x264-GROUP.mkv",
                anitopy_result={
                    "anime_title": "One Piece",
                    "episode_number": "001",
                    "season": "1",
                    "year": 1999,
                    "video_resolution": "1080p",
                    "video_term": "WEB-DL",
                    "file_extension": "mkv",
                },
                expected_tmdb_id=37854,
                expected_title="One Piece",
                expected_media_type="tv",
                confidence_threshold=ConfidenceThresholds.BENCHMARK_MEDIUM,
                notes="Long-running shonen series",
            ),
            GroundTruthEntry(
                filename="Demon.Slayer.Kimetsu.no.Yaiba.S01E01.1080p.WEB-DL.x264-GROUP.mkv",
                anitopy_result={
                    "anime_title": "Demon Slayer: Kimetsu no Yaiba",
                    "episode_number": "01",
                    "season": "1",
                    "year": 2019,
                    "video_resolution": "1080p",
                    "video_term": "WEB-DL",
                    "file_extension": "mkv",
                },
                expected_tmdb_id=101922,
                expected_title="Demon Slayer: Kimetsu no Yaiba",
                expected_media_type="tv",
                confidence_threshold=ConfidenceThresholds.BENCHMARK_MEDIUM,
                notes="Popular modern shonen anime",
            ),
        ]

        dataset = {
            JsonKeys.METADATA: {
                "created_at": datetime.now(timezone.utc).isoformat(),
                JsonKeys.VERSION: "1.0",
                JsonKeys.DESCRIPTION: "Sample ground truth dataset for AniVault matching system",
                JsonKeys.TOTAL_ENTRIES: len(sample_entries),
            },
            JsonKeys.ENTRIES: [asdict(entry) for entry in sample_entries],
        }

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding=Encoding.DEFAULT) as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)

        logger.info(
            "Created sample dataset with %d entries at %s",
            len(sample_entries),
            output_path,
        )

    async def run_benchmark(self) -> tuple[list[BenchmarkResult], BenchmarkSummary]:
        """Run the benchmark against the ground truth dataset.

        This method orchestrates the benchmark process by delegating to specialized methods.

        Returns:
            Tuple of (individual results, summary statistics)
        """
        # Validate prerequisites
        self._validate_benchmark_prerequisites()

        # Initialize benchmark session
        self._initialize_benchmark_session()

        # Run individual test cases
        results = await self._run_individual_tests()

        # Calculate summary statistics
        summary = self._calculate_benchmark_summary(results)

        # Log completion
        self._log_benchmark_completion(summary)

        return results, summary

    def _validate_benchmark_prerequisites(self) -> None:
        """Validate that prerequisites for running benchmark are met."""
        if not self.ground_truth:
            raise ValueError(
                "No ground truth dataset loaded. Call load_ground_truth() first.",
            )

    def _initialize_benchmark_session(self) -> None:
        """Initialize the benchmark session."""
        logger.info("Starting benchmark with %d test cases", len(self.ground_truth))
        self.statistics.reset()

    async def _run_individual_tests(self) -> list[BenchmarkResult]:
        """Run individual test cases and collect results."""
        results = []
        time.time()

        for i, entry in enumerate(self.ground_truth):
            logger.debug(
                "Processing test case %d/%d: %s",
                i + 1,
                len(self.ground_truth),
                entry.filename,
            )

            result = await self._process_single_test_case(entry)
            results.append(result)

        return results

    async def _process_single_test_case(
        self,
        entry: GroundTruthEntry,
    ) -> BenchmarkResult:
        """Process a single test case and return the result."""
        test_start = time.time()

        try:
            # Run the matching
            match_result = await self.matching_engine.find_match(entry.anitopy_result)
            processing_time = time.time() - test_start

            if match_result is None:
                return self._create_no_match_result(entry, processing_time)
            return self._create_match_result(entry, match_result, processing_time)

        except Exception as e:
            processing_time = time.time() - test_start
            logger.exception("Error processing %s", entry.filename)
            return self._create_error_result(entry, str(e), processing_time)

    def _create_no_match_result(
        self,
        entry: GroundTruthEntry,
        processing_time: float,
    ) -> BenchmarkResult:
        """Create a result for when no match was found."""
        return BenchmarkResult(
            filename=entry.filename,
            expected_tmdb_id=entry.expected_tmdb_id,
            actual_tmdb_id=None,
            expected_title=entry.expected_title,
            actual_title=None,
            confidence_score=None,
            is_correct=False,
            processing_time=processing_time,
            error_message="No match found",
        )

    def _create_match_result(
        self,
        entry: GroundTruthEntry,
        match_result: Any,  # Can be MatchResult dataclass or dict (for backward compat)
        processing_time: float,
    ) -> BenchmarkResult:
        """Create a result for when a match was found."""
        # Handle both MatchResult dataclass and dict (backward compatibility)
        if hasattr(match_result, "to_dict"):
            # MatchResult dataclass - convert to dict
            match_dict = match_result.to_dict()
        else:
            # Already a dict
            match_dict = match_result

        actual_tmdb_id = match_dict.get("id")
        actual_title = match_dict.get("title", "")
        confidence_score = match_dict.get("confidence_score", 0.0)

        is_correct = (
            actual_tmdb_id == entry.expected_tmdb_id
            and confidence_score >= entry.confidence_threshold
        )

        return BenchmarkResult(
            filename=entry.filename,
            expected_tmdb_id=entry.expected_tmdb_id,
            actual_tmdb_id=actual_tmdb_id,
            expected_title=entry.expected_title,
            actual_title=actual_title,
            confidence_score=confidence_score,
            is_correct=is_correct,
            processing_time=processing_time,
        )

    def _create_error_result(
        self,
        entry: GroundTruthEntry,
        error_message: str,
        processing_time: float,
    ) -> BenchmarkResult:
        """Create a result for when an error occurred during processing."""
        return BenchmarkResult(
            filename=entry.filename,
            expected_tmdb_id=entry.expected_tmdb_id,
            actual_tmdb_id=None,
            expected_title=entry.expected_title,
            actual_title=None,
            confidence_score=None,
            is_correct=False,
            processing_time=processing_time,
            error_message=error_message,
        )

    def _calculate_benchmark_summary(
        self,
        results: list[BenchmarkResult],
    ) -> BenchmarkSummary:
        """Calculate summary statistics from benchmark results."""
        correct_matches = sum(1 for r in results if r.is_correct)
        incorrect_matches = sum(
            1 for r in results if not r.is_correct and r.actual_tmdb_id is not None
        )
        failed_matches = sum(1 for r in results if r.actual_tmdb_id is None)

        confidence_scores = [
            r.confidence_score for r in results if r.confidence_score is not None
        ]
        average_confidence = (
            sum(confidence_scores) / len(confidence_scores)
            if confidence_scores
            else 0.0
        )

        total_processing_time = sum(r.processing_time for r in results)

        return BenchmarkSummary(
            total_tests=len(results),
            correct_matches=correct_matches,
            incorrect_matches=incorrect_matches,
            failed_matches=failed_matches,
            accuracy=(correct_matches / len(results)) * 100 if results else 0.0,
            average_confidence=average_confidence,
            average_processing_time=(
                total_processing_time / len(results) if results else 0.0
            ),
            total_processing_time=total_processing_time,
            cache_hit_ratio=self.statistics.get_cache_hit_ratio(),
            api_calls=self.statistics.metrics.api_calls,
            api_errors=self.statistics.metrics.api_errors,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _log_benchmark_completion(self, summary: BenchmarkSummary) -> None:
        """Log benchmark completion with summary statistics."""
        logger.info(
            "Benchmark completed: %d tests, %.1f%% accuracy, %.2fs total time",
            summary.total_tests,
            summary.accuracy,
            summary.total_processing_time,
        )

    def save_results(
        self,
        results: list[BenchmarkResult],
        summary: BenchmarkSummary,
        output_path: Path | str,
    ) -> None:
        """Save benchmark results to JSON file.

        Args:
            results: Individual benchmark results
            summary: Summary statistics
            output_path: Path where to save the results
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "summary": asdict(summary),
            "results": [asdict(result) for result in results],
            "statistics": self.statistics.get_summary(),
        }

        with open(output_path, "w", encoding=Encoding.DEFAULT) as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info("Saved benchmark results to %s", output_path)

    def print_summary(self, summary: BenchmarkSummary) -> None:
        """Print a formatted summary of benchmark results.

        Args:
            summary: Summary statistics to print
        """
        print("\n" + "=" * CLIFormatting.SEPARATOR_LENGTH)
        print("BENCHMARK RESULTS SUMMARY")
        print("=" * CLIFormatting.SEPARATOR_LENGTH)
        print(f"Total Tests:           {summary.total_tests}")
        print(f"Correct Matches:       {summary.correct_matches}")
        print(f"Incorrect Matches:     {summary.incorrect_matches}")
        print(f"Failed Matches:        {summary.failed_matches}")
        print(f"Accuracy:              {summary.accuracy:.1f}%")
        print(f"Average Confidence:    {summary.average_confidence:.3f}")
        print(f"Average Processing:    {summary.average_processing_time:.3f}s")
        print(f"Total Processing:      {summary.total_processing_time:.3f}s")
        print(f"Cache Hit Ratio:       {summary.cache_hit_ratio:.1f}%")
        print(f"API Calls:             {summary.api_calls}")
        print(f"API Errors:            {summary.api_errors}")
        print("=" * CLIFormatting.SEPARATOR_LENGTH)
