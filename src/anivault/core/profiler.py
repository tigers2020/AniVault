"""
Profiling and Report Generation Module

This module provides comprehensive profiling capabilities and detailed report
generation for the AniVault matching system, including performance analysis,
memory usage tracking, and detailed statistical reporting.
"""

from __future__ import annotations

import json
import logging
import platform
import time
import tracemalloc
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil

from anivault.core.statistics import PerformanceMetrics, StatisticsCollector

logger = logging.getLogger(__name__)


@dataclass
class MemorySnapshot:
    """Memory usage snapshot at a specific point in time.

    Attributes:
        timestamp: When the snapshot was taken
        current_memory_mb: Current memory usage in MB
        peak_memory_mb: Peak memory usage in MB
        memory_blocks: Number of memory blocks allocated
        context: Context description for this snapshot
    """

    timestamp: str
    current_memory_mb: float
    peak_memory_mb: float
    memory_blocks: int
    context: str


@dataclass
class ProfilingReport:
    """Comprehensive profiling report.

    Attributes:
        session_id: Unique session identifier
        start_time: When profiling started
        end_time: When profiling ended
        duration_seconds: Total profiling duration
        memory_snapshots: List of memory snapshots taken
        performance_metrics: Performance metrics collected
        system_info: System information
        recommendations: Performance improvement recommendations
    """

    session_id: str
    start_time: str
    end_time: str
    duration_seconds: float
    memory_snapshots: list[MemorySnapshot]
    performance_metrics: PerformanceMetrics
    system_info: dict[str, Any]
    recommendations: list[str]


class Profiler:
    """Comprehensive profiler for performance analysis and reporting.

    This class provides detailed profiling capabilities including memory
    tracking, performance monitoring, and comprehensive report generation
    for the AniVault matching system.
    """

    def __init__(self, statistics: StatisticsCollector | None = None):
        """Initialize the profiler.

        Args:
            statistics: Optional statistics collector for performance tracking
        """
        self.statistics = statistics or StatisticsCollector()
        self.session_id = f"profiler_{int(time.time())}"
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None
        self.memory_snapshots: list[MemorySnapshot] = []
        self.tracemalloc_started = False

        logger.info("Initialized Profiler with session_id=%s", self.session_id)

    def start_profiling(self) -> None:
        """Start profiling session."""
        self.start_time = datetime.now(timezone.utc)

        # Start memory tracing
        if not self.tracemalloc_started:
            tracemalloc.start()
            self.tracemalloc_started = True

        # Reset statistics
        self.statistics.reset()

        logger.info("Started profiling session: %s", self.session_id)

    def stop_profiling(self) -> None:
        """Stop profiling session."""
        self.end_time = datetime.now(timezone.utc)

        # Stop memory tracing
        if self.tracemalloc_started:
            tracemalloc.stop()
            self.tracemalloc_started = False

        logger.info("Stopped profiling session: %s", self.session_id)

    def take_memory_snapshot(self, context: str = "manual") -> MemorySnapshot:
        """Take a memory usage snapshot.

        Args:
            context: Context description for this snapshot

        Returns:
            Memory snapshot with current usage information
        """
        if not self.tracemalloc_started:
            logger.warning("Memory tracing not started, cannot take snapshot")
            return MemorySnapshot(
                timestamp=datetime.now(timezone.utc).isoformat(),
                current_memory_mb=0.0,
                peak_memory_mb=0.0,
                memory_blocks=0,
                context=context,
            )

        # Get current memory usage
        current, peak = tracemalloc.get_traced_memory()
        current_mb = current / 1024 / 1024
        peak_mb = peak / 1024 / 1024

        # Get memory block count
        snapshot = tracemalloc.take_snapshot()
        memory_blocks = len(snapshot.traces)

        snapshot_data = MemorySnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            current_memory_mb=current_mb,
            peak_memory_mb=peak_mb,
            memory_blocks=memory_blocks,
            context=context,
        )

        self.memory_snapshots.append(snapshot_data)

        logger.debug(
            "Memory snapshot taken: %.2f MB current, %.2f MB peak, %d blocks",
            current_mb,
            peak_mb,
            memory_blocks,
        )

        return snapshot_data

    @contextmanager
    def profile_section(self, section_name: str) -> Generator[None, None, None]:
        """Context manager for profiling a specific code section.

        Args:
            section_name: Name of the section being profiled
        """
        start_time = time.time()
        start_memory = self.take_memory_snapshot(f"start_{section_name}")

        try:
            yield
        finally:
            end_time = time.time()
            end_memory = self.take_memory_snapshot(f"end_{section_name}")

            duration = end_time - start_time
            memory_delta = end_memory.current_memory_mb - start_memory.current_memory_mb

            logger.debug(
                "Section '%s' completed in %.3fs, memory delta: %.2f MB",
                section_name,
                duration,
                memory_delta,
            )

    def get_system_info(self) -> dict[str, Any]:
        """Get system information for profiling report.

        Returns:
            Dictionary containing system information
        """

        try:
            return {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": psutil.virtual_memory().total / (1024**3),
                "memory_available_gb": psutil.virtual_memory().available / (1024**3),
                "disk_usage_percent": psutil.disk_usage("/").percent,
            }
        except ImportError:
            logger.warning("psutil not available, returning basic system info")
            return {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "cpu_count": platform.processor(),
            }

    def generate_recommendations(self) -> list[str]:
        """Generate performance improvement recommendations.

        This method orchestrates the recommendation generation by delegating to specialized methods.

        Returns:
            List of performance improvement recommendations
        """
        recommendations = []
        metrics = self.statistics.metrics

        # Generate cache performance recommendations
        recommendations.extend(self._generate_cache_recommendations(metrics))

        # Generate API performance recommendations
        recommendations.extend(self._generate_api_recommendations(metrics))

        # Generate memory usage recommendations
        recommendations.extend(self._generate_memory_recommendations())

        # Generate processing time recommendations
        recommendations.extend(self._generate_processing_time_recommendations(metrics))

        # Generate matching accuracy recommendations
        recommendations.extend(self._generate_accuracy_recommendations(metrics))

        return recommendations

    def _generate_cache_recommendations(self, metrics: PerformanceMetrics) -> list[str]:
        """Generate cache performance recommendations."""
        recommendations = []

        if metrics.cache_hit_ratio < 50.0:
            recommendations.append(
                "Low cache hit ratio detected. Consider increasing cache TTL or "
                "implementing more aggressive caching strategies.",
            )

        return recommendations

    def _generate_api_recommendations(self, metrics: PerformanceMetrics) -> list[str]:
        """Generate API performance recommendations."""
        recommendations = []

        if metrics.api_errors > 0:
            error_rate = (metrics.api_errors / max(metrics.api_calls, 1)) * 100
            if error_rate > 10.0:
                recommendations.append(
                    f"High API error rate detected ({error_rate:.1f}%). "
                    "Consider implementing retry logic or rate limiting.",
                )

        return recommendations

    def _generate_memory_recommendations(self) -> list[str]:
        """Generate memory usage recommendations."""
        recommendations = []

        if self.memory_snapshots:
            peak_memory = max(
                snapshot.peak_memory_mb for snapshot in self.memory_snapshots
            )
            if peak_memory > 1000:  # 1GB
                recommendations.append(
                    f"High memory usage detected ({peak_memory:.1f} MB peak). "
                    "Consider implementing memory optimization strategies.",
                )

        return recommendations

    def _generate_processing_time_recommendations(
        self,
        metrics: PerformanceMetrics,
    ) -> list[str]:
        """Generate processing time recommendations."""
        recommendations = []

        if metrics.average_memory_mb > 0:
            avg_processing_time = metrics.total_time / max(metrics.total_files, 1)
            if avg_processing_time > 5.0:  # 5 seconds per file
                recommendations.append(
                    f"Slow processing detected ({avg_processing_time:.1f}s per file). "
                    "Consider optimizing matching algorithms or implementing parallel processing.",
                )

        return recommendations

    def _generate_accuracy_recommendations(
        self,
        metrics: PerformanceMetrics,
    ) -> list[str]:
        """Generate matching accuracy recommendations."""
        recommendations = []

        if metrics.total_files > 0:
            success_rate = (metrics.successful_matches / metrics.total_files) * 100
            if success_rate < 70.0:
                recommendations.append(
                    f"Low matching accuracy detected ({success_rate:.1f}%). "
                    "Consider improving normalization or confidence scoring algorithms.",
                )

        return recommendations

    def generate_report(self) -> ProfilingReport:
        """Generate comprehensive profiling report.

        Returns:
            Complete profiling report with all collected data
        """
        if not self.start_time:
            raise ValueError("Profiling not started. Call start_profiling() first.")

        end_time = self.end_time or datetime.now(timezone.utc)
        duration = (end_time - self.start_time).total_seconds()

        report = ProfilingReport(
            session_id=self.session_id,
            start_time=self.start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration,
            memory_snapshots=self.memory_snapshots.copy(),
            performance_metrics=self.statistics.metrics,
            system_info=self.get_system_info(),
            recommendations=self.generate_recommendations(),
        )

        logger.info("Generated profiling report for session %s", self.session_id)
        return report

    def save_report(self, report: ProfilingReport, output_path: Path | str) -> None:
        """Save profiling report to JSON file.

        Args:
            report: Profiling report to save
            output_path: Path where to save the report
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert dataclasses to dictionaries for JSON serialization
        report_dict = asdict(report)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        logger.info("Saved profiling report to %s", output_path)

    def print_summary(self, report: ProfilingReport) -> None:
        """Print a formatted summary of the profiling report.

        Args:
            report: Profiling report to summarize
        """
        print("\n" + "=" * 80)
        print("PROFILING REPORT SUMMARY")
        print("=" * 80)
        print(f"Session ID:             {report.session_id}")
        print(f"Start Time:             {report.start_time}")
        print(f"End Time:               {report.end_time}")
        print(f"Duration:               {report.duration_seconds:.2f} seconds")
        print()

        # Performance Metrics
        print("PERFORMANCE METRICS:")
        print("-" * 40)
        metrics = report.performance_metrics
        print(f"Total Files:            {metrics.total_files}")
        print(f"Successful Matches:     {metrics.successful_matches}")
        print(f"Failed Matches:         {metrics.failed_matches}")
        print(f"Cache Hits:             {metrics.cache_hits}")
        print(f"Cache Misses:           {metrics.cache_misses}")
        print(f"Cache Hit Ratio:        {metrics.cache_hit_ratio:.1f}%")
        print(f"API Calls:              {metrics.api_calls}")
        print(f"API Errors:             {metrics.api_errors}")
        print(f"Peak Memory:            {metrics.peak_memory_mb:.2f} MB")
        print(f"Average Memory:         {metrics.average_memory_mb:.2f} MB")
        print()

        # Memory Snapshots
        if report.memory_snapshots:
            print("MEMORY SNAPSHOTS:")
            print("-" * 40)
            for snapshot in report.memory_snapshots:
                print(
                    f"{snapshot.timestamp}: {snapshot.current_memory_mb:.2f} MB "
                    f"(peak: {snapshot.peak_memory_mb:.2f} MB) - {snapshot.context}",
                )
            print()

        # System Information
        print("SYSTEM INFORMATION:")
        print("-" * 40)
        for key, value in report.system_info.items():
            print(f"{key.replace('_', ' ').title()}: {value}")
        print()

        # Recommendations
        if report.recommendations:
            print("RECOMMENDATIONS:")
            print("-" * 40)
            for i, rec in enumerate(report.recommendations, 1):
                print(f"{i}. {rec}")
            print()

        print("=" * 80)

    def export_detailed_analysis(
        self,
        report: ProfilingReport,
        output_path: Path | str,
    ) -> None:
        """Export detailed analysis to a comprehensive report file.

        This method orchestrates the detailed analysis export by delegating to specialized methods.

        Args:
            report: Profiling report to analyze
            output_path: Path where to save the detailed analysis
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate comprehensive analysis
        analysis = self._generate_comprehensive_analysis(report)

        # Write analysis to file
        self._write_analysis_to_file(output_path, analysis)

        logger.info("Exported detailed analysis to %s", output_path)

    def _generate_comprehensive_analysis(
        self,
        report: ProfilingReport,
    ) -> dict[str, Any]:
        """Generate comprehensive analysis from profiling report."""
        return {
            "session_summary": self._generate_session_summary(report),
            "performance_analysis": self._generate_performance_analysis(report),
            "memory_analysis": self._generate_memory_analysis(report),
            "recommendations": report.recommendations,
            "system_info": report.system_info,
        }

    def _generate_session_summary(self, report: ProfilingReport) -> dict[str, Any]:
        """Generate session summary from profiling report."""
        return {
            "session_id": report.session_id,
            "duration_seconds": report.duration_seconds,
            "start_time": report.start_time,
            "end_time": report.end_time,
        }

    def _generate_performance_analysis(self, report: ProfilingReport) -> dict[str, Any]:
        """Generate performance analysis from profiling report."""
        metrics = report.performance_metrics

        return {
            "throughput": self._calculate_throughput_metrics(report, metrics),
            "accuracy": self._calculate_accuracy_metrics(metrics),
            "efficiency": self._calculate_efficiency_metrics(metrics),
        }

    def _calculate_throughput_metrics(
        self,
        report: ProfilingReport,
        metrics: PerformanceMetrics,
    ) -> dict[str, float]:
        """Calculate throughput metrics."""
        duration = max(report.duration_seconds, 1)

        return {
            "files_per_second": metrics.total_files / duration,
            "matches_per_second": metrics.successful_matches / duration,
        }

    def _calculate_accuracy_metrics(
        self,
        metrics: PerformanceMetrics,
    ) -> dict[str, float]:
        """Calculate accuracy metrics."""
        total_files = max(metrics.total_files, 1)
        successful_matches = max(metrics.successful_matches, 1)

        return {
            "success_rate": (metrics.successful_matches / total_files) * 100,
            "high_confidence_rate": (
                metrics.high_confidence_matches / successful_matches
            )
            * 100,
        }

    def _calculate_efficiency_metrics(
        self,
        metrics: PerformanceMetrics,
    ) -> dict[str, float]:
        """Calculate efficiency metrics."""
        api_calls = max(metrics.api_calls, 1)

        return {
            "cache_efficiency": metrics.cache_hit_ratio,
            "api_efficiency": ((api_calls - metrics.api_errors) / api_calls) * 100,
        }

    def _generate_memory_analysis(self, report: ProfilingReport) -> dict[str, Any]:
        """Generate memory analysis from profiling report."""
        return {
            "peak_usage_mb": report.performance_metrics.peak_memory_mb,
            "average_usage_mb": report.performance_metrics.average_memory_mb,
            "snapshots_count": len(report.memory_snapshots),
            "memory_growth": self._calculate_memory_growth(report.memory_snapshots),
        }

    def _write_analysis_to_file(
        self,
        output_path: Path,
        analysis: dict[str, Any],
    ) -> None:
        """Write analysis data to file."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)

    def _calculate_memory_growth(
        self,
        snapshots: list[MemorySnapshot],
    ) -> dict[str, float]:
        """Calculate memory growth patterns from snapshots.

        Args:
            snapshots: List of memory snapshots

        Returns:
            Dictionary with memory growth analysis
        """
        if len(snapshots) < 2:
            return {"growth_rate_mb_per_snapshot": 0.0, "total_growth_mb": 0.0}

        first_snapshot = snapshots[0]
        last_snapshot = snapshots[-1]

        total_growth = (
            last_snapshot.current_memory_mb - first_snapshot.current_memory_mb
        )
        growth_rate = total_growth / (len(snapshots) - 1)

        return {
            "growth_rate_mb_per_snapshot": growth_rate,
            "total_growth_mb": total_growth,
        }
