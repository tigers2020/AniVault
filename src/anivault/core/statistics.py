"""
Statistics Collection and Performance Benchmarking Module

This module provides comprehensive statistics collection and performance
benchmarking capabilities for the AniVault matching system.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from anivault.shared.constants import (
    HIGH_CONFIDENCE_THRESHOLD,
    MEDIUM_CONFIDENCE_THRESHOLD,
)

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""

    # Timing metrics
    total_time: float = 0.0
    matching_time: float = 0.0
    cache_time: float = 0.0
    api_time: float = 0.0

    # Cache metrics
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_ratio: float = 0.0

    # Matching metrics
    total_files: int = 0
    successful_matches: int = 0
    failed_matches: int = 0
    high_confidence_matches: int = 0
    medium_confidence_matches: int = 0
    low_confidence_matches: int = 0

    # API metrics
    api_calls: int = 0
    api_errors: int = 0
    rate_limit_hits: int = 0

    # Memory metrics
    peak_memory_mb: float = 0.0
    average_memory_mb: float = 0.0

    def __post_init__(self) -> None:
        """Calculate derived metrics after initialization."""
        self.cache_hit_ratio = (
            self.cache_hits / (self.cache_hits + self.cache_misses)
            if (self.cache_hits + self.cache_misses) > 0
            else 0.0
        )

        self.match_success_rate = (
            self.successful_matches / self.total_files if self.total_files > 0 else 0.0
        )


@dataclass
class BenchmarkResult:
    """Container for benchmark test results."""

    test_name: str
    start_time: datetime
    end_time: datetime
    duration: float
    metrics: PerformanceMetrics
    success: bool
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Calculate duration if not provided."""
        if self.duration == 0.0:
            self.duration = (self.end_time - self.start_time).total_seconds()


class StatisticsCollector:
    """Central aggregator for all performance and accuracy metrics."""

    def __init__(self) -> None:
        """Initialize the statistics collector."""
        self.metrics = PerformanceMetrics()
        self.benchmark_results: list[BenchmarkResult] = []
        self.session_start = datetime.now(timezone.utc)
        self.timing_stack: list[float] = []

        # Detailed tracking
        self.file_metrics: dict[str, dict[str, Any]] = defaultdict(dict)
        self.api_call_times: list[float] = []
        self.cache_operations: list[dict[str, Any]] = []

        logger.info("StatisticsCollector initialized")

    def start_timing(self, operation: str) -> None:
        """Start timing an operation.

        Args:
            operation: Name of the operation being timed
        """
        self.timing_stack.append(time.time())
        logger.debug("Started timing operation: %s", operation)

    def end_timing(self, operation: str) -> float:
        """End timing an operation and return duration.

        Args:
            operation: Name of the operation being timed

        Returns:
            Duration in seconds
        """
        if not self.timing_stack:
            logger.warning("No timing started for operation: %s", operation)
            return 0.0

        start_time = self.timing_stack.pop()
        duration = time.time() - start_time

        logger.debug("Ended timing operation: %s, duration: %.3fs", operation, duration)
        return duration

    def record_matching_operation(
        self,
        file_path: str,
        success: bool,
        confidence: float | None = None,
        duration: float | None = None,
        used_fallback: bool = False,
    ) -> None:
        """Record a matching operation.

        Args:
            file_path: Path to the file being matched
            success: Whether the matching was successful
            confidence: Confidence score of the match (0.0-1.0)
            duration: Duration of the matching operation
            used_fallback: Whether fallback strategies were used
        """
        self.metrics.total_files += 1

        if success:
            self.metrics.successful_matches += 1

            if confidence is not None:
                if confidence >= HIGH_CONFIDENCE_THRESHOLD:
                    self.metrics.high_confidence_matches += 1
                elif confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
                    self.metrics.medium_confidence_matches += 1
                else:
                    self.metrics.low_confidence_matches += 1
        else:
            self.metrics.failed_matches += 1

        # Store detailed metrics for this file
        self.file_metrics[file_path] = {
            "success": success,
            "confidence": confidence,
            "duration": duration,
            "used_fallback": used_fallback,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.debug(
            "Recorded matching operation for %s: success=%s, confidence=%s",
            file_path, success, confidence,
        )

    def record_cache_operation(
        self,
        operation: str,
        hit: bool,
        duration: float | None = None,
        key: str | None = None,
    ) -> None:
        """Record a cache operation.

        Args:
            operation: Type of cache operation (get, set, delete)
            hit: Whether it was a cache hit
            duration: Duration of the operation
            key: Cache key used
        """
        if operation == "get":
            if hit:
                self.metrics.cache_hits += 1
            else:
                self.metrics.cache_misses += 1

        # Store detailed cache operation
        self.cache_operations.append(
            {
                "operation": operation,
                "hit": hit,
                "duration": duration,
                "key": key,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.debug("Recorded cache operation: %s, hit=%s", operation, hit)

    def record_api_call(
        self,
        endpoint: str,
        success: bool,
        duration: float | None = None,
        error: str | None = None,  # noqa: ARG002
    ) -> None:
        """Record an API call.

        Args:
            endpoint: API endpoint called
            success: Whether the call was successful
            duration: Duration of the API call
            error: Error message if the call failed
        """
        self.metrics.api_calls += 1

        if not success:
            self.metrics.api_errors += 1

        if duration is not None:
            self.api_call_times.append(duration)
            self.metrics.api_time += duration

        logger.debug(
            "Recorded API call: %s, success=%s, duration=%s",
            endpoint,
            success,
            duration,
        )

    def record_rate_limit_hit(self) -> None:
        """Record a rate limit hit."""
        self.metrics.rate_limit_hits += 1
        logger.debug("Recorded rate limit hit")

    def record_memory_usage(self, memory_mb: float) -> None:
        """Record current memory usage.

        Args:
            memory_mb: Memory usage in megabytes
        """
        self.metrics.peak_memory_mb = max(memory_mb, self.metrics.peak_memory_mb)

        # Update average memory usage using a separate counter
        if not hasattr(self, "_memory_samples"):
            self._memory_samples = 0
            self._memory_sum = 0.0

        self._memory_samples += 1
        self._memory_sum += memory_mb
        self.metrics.average_memory_mb = self._memory_sum / self._memory_samples

        logger.debug("Recorded memory usage: %.2f MB", memory_mb)

    def record_cache_hit(self, cache_type: str) -> None:
        """Record a cache hit.

        Args:
            cache_type: Type of cache (search, metadata, etc.)
        """
        self.metrics.cache_hits += 1
        logger.debug("Recorded cache hit for type: %s", cache_type)

    def record_cache_miss(self, cache_type: str) -> None:
        """Record a cache miss.

        Args:
            cache_type: Type of cache (search, metadata, etc.)
        """
        self.metrics.cache_misses += 1
        logger.debug("Recorded cache miss for type: %s", cache_type)

    def record_match_success(
        self,
        confidence: float,
        candidates_count: int,
        used_fallback: bool = False,
    ) -> None:
        """Record a successful match.

        Args:
            confidence: Confidence score of the match
            candidates_count: Number of candidates considered
            used_fallback: Whether fallback strategies were used
        """
        self.metrics.successful_matches += 1

        # Categorize by confidence level
        if confidence >= HIGH_CONFIDENCE_THRESHOLD:
            self.metrics.high_confidence_matches += 1
        elif confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
            self.metrics.medium_confidence_matches += 1
        else:
            self.metrics.low_confidence_matches += 1

        logger.debug(
            "Recorded successful match: confidence=%.3f, candidates=%d, fallback=%s",
            confidence,
            candidates_count,
            used_fallback,
        )

    def record_match_failure(self) -> None:
        """Record a failed match."""
        self.metrics.failed_matches += 1
        logger.debug("Recorded match failure")

    def record_api_error(self, api_type: str) -> None:
        """Record an API error.

        Args:
            api_type: Type of API call that failed
        """
        self.metrics.api_errors += 1
        logger.debug("Recorded API error for type: %s", api_type)

    def get_cache_hit_ratio(self) -> float:
        """Get the current cache hit ratio.

        Returns:
            Cache hit ratio as a percentage (0.0 to 100.0)
        """
        total_requests = self.metrics.cache_hits + self.metrics.cache_misses
        if total_requests == 0:
            return 0.0
        return (self.metrics.cache_hits / total_requests) * 100.0

    def start_benchmark(self, test_name: str) -> None:
        """Start a benchmark test.

        Args:
            test_name: Name of the benchmark test
        """
        self.start_timing("benchmark_" + test_name)
        logger.info("Started benchmark: %s", test_name)

    def end_benchmark(
        self,
        test_name: str,
        success: bool = True,
        error_message: str | None = None,
    ) -> BenchmarkResult:
        """End a benchmark test and create a result.

        Args:
            test_name: Name of the benchmark test
            success: Whether the benchmark was successful
            error_message: Error message if the benchmark failed

        Returns:
            BenchmarkResult object
        """
        duration = self.end_timing("benchmark_" + test_name)

        result = BenchmarkResult(
            test_name=test_name,
            start_time=self.session_start,  # Simplified for now
            end_time=datetime.now(timezone.utc),
            duration=duration,
            metrics=self.metrics,
            success=success,
            error_message=error_message,
        )

        self.benchmark_results.append(result)
        logger.info(
            "Ended benchmark: %s, success=%s, duration=%.3fs",
            test_name,
            success,
            duration,
        )

        return result

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all collected statistics.

        Returns:
            Dictionary containing summary statistics
        """
        session_duration = (
            datetime.now(timezone.utc) - self.session_start
        ).total_seconds()

        return {
            "session_info": {
                "start_time": self.session_start.isoformat(),
                "duration_seconds": session_duration,
                "total_benchmarks": len(self.benchmark_results),
            },
            "performance_metrics": {
                "total_files": self.metrics.total_files,
                "successful_matches": self.metrics.successful_matches,
                "failed_matches": self.metrics.failed_matches,
                "match_success_rate": self.metrics.match_success_rate,
                "high_confidence_matches": self.metrics.high_confidence_matches,
                "medium_confidence_matches": self.metrics.medium_confidence_matches,
                "low_confidence_matches": self.metrics.low_confidence_matches,
                "cache_hits": self.metrics.cache_hits,
                "cache_misses": self.metrics.cache_misses,
                "cache_hit_ratio": self.metrics.cache_hit_ratio,
                "api_calls": self.metrics.api_calls,
                "api_errors": self.metrics.api_errors,
                "rate_limit_hits": self.metrics.rate_limit_hits,
                "total_time": self.metrics.total_time,
                "matching_time": self.metrics.matching_time,
                "cache_time": self.metrics.cache_time,
                "api_time": self.metrics.api_time,
                "peak_memory_mb": self.metrics.peak_memory_mb,
                "average_memory_mb": self.metrics.average_memory_mb,
            },
            "detailed_metrics": {
                "file_metrics_count": len(self.file_metrics),
                "cache_operations_count": len(self.cache_operations),
                "api_call_times_count": len(self.api_call_times),
            },
        }

    def reset(self) -> None:
        """Reset all collected statistics."""
        self.metrics = PerformanceMetrics()
        self.benchmark_results.clear()
        self.session_start = datetime.now(timezone.utc)
        self.timing_stack.clear()
        self.file_metrics.clear()
        self.api_call_times.clear()
        self.cache_operations.clear()

        # Reset memory tracking
        if hasattr(self, "_memory_samples"):
            self._memory_samples = 0
            self._memory_sum = 0.0

        logger.info("StatisticsCollector reset")

    def export_to_json(self) -> dict[str, Any]:
        """Export all statistics to a JSON-serializable format.

        Returns:
            Dictionary containing all statistics data
        """
        return {
            "summary": self.get_summary(),
            "file_metrics": dict(self.file_metrics),
            "cache_operations": self.cache_operations,
            "api_call_times": self.api_call_times,
            "benchmark_results": [
                {
                    "test_name": result.test_name,
                    "start_time": result.start_time.isoformat(),
                    "end_time": result.end_time.isoformat(),
                    "duration": result.duration,
                    "success": result.success,
                    "error_message": result.error_message,
                }
                for result in self.benchmark_results
            ],
        }


# Global statistics collector instance
_global_collector: StatisticsCollector | None = None


def get_statistics_collector() -> StatisticsCollector:
    """Get the global statistics collector instance.

    Returns:
        StatisticsCollector instance
    """
    global _global_collector
    if _global_collector is None:
        _global_collector = StatisticsCollector()
    return _global_collector


def reset_statistics() -> None:
    """Reset the global statistics collector."""
    global _global_collector  # noqa: PLW0602
    if _global_collector is not None:
        _global_collector.reset()
