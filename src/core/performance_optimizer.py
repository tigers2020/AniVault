"""Performance optimization module for AniVault application.

This module provides performance testing, profiling, and optimization utilities
for the file scanning and grouping operations.
"""

from __future__ import annotations

import gc
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psutil

from .file_grouper import FileGrouper, GroupingResult
from .file_scanner import FileScanner, ScanResult
from .models import AnimeFile, FileGroup


@dataclass
class PerformanceMetrics:
    """Performance metrics for an operation."""

    operation_name: str
    duration: float
    memory_usage_mb: float
    cpu_usage_percent: float
    files_processed: int
    files_per_second: float
    memory_per_file_mb: float
    peak_memory_mb: float
    thread_count: int

    @property
    def efficiency_score(self) -> float:
        """Calculate an efficiency score based on performance metrics."""
        # Higher is better
        files_per_second_score = min(self.files_per_second / 100, 1.0)  # Cap at 100 files/sec
        memory_efficiency = max(
            0, 1.0 - (self.memory_per_file_mb / 10)
        )  # Lower memory per file is better
        return (files_per_second_score + memory_efficiency) / 2


class PerformanceProfiler:
    """Profiler for measuring and optimizing performance."""

    def __init__(self) -> None:
        """Initialize the performance profiler."""
        self.metrics_history: list[PerformanceMetrics] = []
        self._monitoring = False
        self._monitor_thread: threading.Thread | None = None
        self._peak_memory = 0.0
        self._start_memory = 0.0

    def start_monitoring(self) -> None:
        """Start monitoring system resources."""
        self._monitoring = True
        self._start_memory = self._get_memory_usage()
        self._peak_memory = self._start_memory

        def monitor() -> None:
            while self._monitoring:
                current_memory = self._get_memory_usage()
                self._peak_memory = max(self._peak_memory, current_memory)
                time.sleep(0.1)  # Check every 100ms

        self._monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self) -> tuple[float, float]:
        """Stop monitoring and return memory usage stats."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)

        current_memory = self._get_memory_usage()
        return current_memory, self._peak_memory

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return float(process.memory_info().rss) / (1024 * 1024)

    def profile_operation(
        self, operation_name: str, operation: Callable[[], Any], files_processed: int = 0
    ) -> PerformanceMetrics:
        """Profile a single operation and return metrics."""
        self.start_monitoring()
        start_time = time.time()

        try:
            operation()
        finally:
            end_time = time.time()
            current_memory, peak_memory = self.stop_monitoring()

        duration = end_time - start_time
        memory_usage = current_memory - self._start_memory
        cpu_usage = psutil.cpu_percent(interval=0.1)
        thread_count = threading.active_count()

        files_per_second = files_processed / duration if duration > 0 else 0
        memory_per_file = memory_usage / files_processed if files_processed > 0 else 0

        metrics = PerformanceMetrics(
            operation_name=operation_name,
            duration=duration,
            memory_usage_mb=memory_usage,
            cpu_usage_percent=cpu_usage,
            files_processed=files_processed,
            files_per_second=files_per_second,
            memory_per_file_mb=memory_per_file,
            peak_memory_mb=peak_memory,
            thread_count=thread_count,
        )

        self.metrics_history.append(metrics)
        return metrics

    def get_optimization_recommendations(self) -> list[str]:
        """Get performance optimization recommendations based on metrics history."""
        if not self.metrics_history:
            return ["No performance data available"]

        recommendations = []
        latest_metrics = self.metrics_history[-1]

        # Check files per second
        if latest_metrics.files_per_second < 50:
            recommendations.append("Consider increasing max_workers for parallel processing")

        # Check memory usage
        if latest_metrics.memory_per_file_mb > 5:
            recommendations.append("High memory usage per file - consider batch processing")

        # Check CPU usage
        if latest_metrics.cpu_usage_percent < 50:
            recommendations.append("CPU usage is low - consider increasing parallelism")
        elif latest_metrics.cpu_usage_percent > 90:
            recommendations.append("High CPU usage - consider reducing max_workers")

        # Check thread count
        if latest_metrics.thread_count > 20:
            recommendations.append("High thread count - consider reducing max_workers")

        return recommendations


def performance_test(
    test_directory: Path,
    file_count_target: int = 1000,
    similarity_threshold: float = 0.75,
    max_workers: int = 4,
) -> dict[str, Any]:
    """Run a comprehensive performance test of the file scanning and grouping system.

    Args:
        test_directory: Directory to test with
        file_count_target: Target number of files to process
        similarity_threshold: Similarity threshold for grouping
        max_workers: Number of worker threads

    Returns:
        Dictionary containing performance results and recommendations
    """
    profiler = PerformanceProfiler()
    results: dict[str, Any] = {
        "scan_results": None,
        "grouping_results": None,
        "scan_metrics": None,
        "grouping_metrics": None,
        "total_duration": 0.0,
        "total_files_processed": 0,
        "recommendations": [],
    }

    try:
        # Test file scanning
        def scan_operation() -> ScanResult:
            scanner = FileScanner(max_workers=max_workers)
            return scanner.scan_directory(test_directory, recursive=True)

        scan_metrics = profiler.profile_operation("File Scanning", scan_operation)

        scan_result = scan_operation()
        results["scan_results"] = scan_result
        results["scan_metrics"] = scan_metrics

        # Test file grouping
        if scan_result.files:

            def grouping_operation() -> GroupingResult:
                grouper = FileGrouper(
                    similarity_threshold=similarity_threshold, max_workers=max_workers
                )
                return grouper.group_files(scan_result.files)

            grouping_metrics = profiler.profile_operation(
                "File Grouping", grouping_operation, files_processed=len(scan_result.files)
            )

            grouping_result = grouping_operation()
            results["grouping_results"] = grouping_result
            results["grouping_metrics"] = grouping_metrics

        # Calculate totals
        results["total_duration"] = scan_metrics.duration
        results["total_files_processed"] = scan_metrics.files_processed
        if results.get("grouping_metrics"):
            results["total_duration"] += results["grouping_metrics"].duration

        # Get recommendations
        results["recommendations"] = profiler.get_optimization_recommendations()

    except Exception as e:
        results["error"] = str(e)

    return results


class OptimizedFileProcessor:
    """Optimized file processor that combines scanning and grouping with performance optimizations."""

    def __init__(
        self,
        similarity_threshold: float = 0.75,
        max_workers: int | None = None,
        batch_size: int = 100,
        enable_caching: bool = True,
    ) -> None:
        """Initialize the optimized file processor.

        Args:
            similarity_threshold: Similarity threshold for grouping
            max_workers: Number of worker threads (auto-detect if None)
            batch_size: Number of files to process in each batch
            enable_caching: Whether to enable file metadata caching
        """
        self.similarity_threshold = similarity_threshold
        self.max_workers = max_workers or min(psutil.cpu_count(), 8)
        self.batch_size = batch_size
        self.enable_caching = enable_caching

        # Cache for file metadata
        self._file_cache: dict[str, AnimeFile] = {}
        self._cache_lock = threading.Lock()

    def process_directory(
        self, directory: Path, progress_callback: Callable[[int, str], None] | None = None
    ) -> tuple[ScanResult, GroupingResult]:
        """Process a directory with optimized scanning and grouping.

        Args:
            directory: Directory to process
            progress_callback: Optional progress callback

        Returns:
            Tuple of (ScanResult, GroupingResult)
        """
        # Phase 1: Optimized scanning
        if progress_callback:
            progress_callback(0, "Starting optimized file scanning...")

        scanner = FileScanner(
            max_workers=self.max_workers,
            progress_callback=lambda p, msg: (
                progress_callback(p // 2, f"Scanning: {msg}") if progress_callback else None
            ),
        )

        scan_result = scanner.scan_directory(directory, recursive=True)

        if not scan_result.files:
            return scan_result, GroupingResult(
                groups=[],
                ungrouped_files=[],
                grouping_duration=0.0,
                total_files=0,
                grouped_files=0,
                similarity_threshold=self.similarity_threshold,
                errors=[],
            )

        # Phase 2: Optimized grouping with batching
        if progress_callback:
            progress_callback(50, "Starting optimized file grouping...")

        grouper = FileGrouper(
            similarity_threshold=self.similarity_threshold,
            max_workers=self.max_workers,
            progress_callback=lambda p, msg: (
                progress_callback(50 + p // 2, f"Grouping: {msg}") if progress_callback else None
            ),
        )

        # Process files in batches for better memory management
        if len(scan_result.files) > self.batch_size:
            grouping_result = self._process_files_in_batches(
                scan_result.files, grouper, progress_callback
            )
        else:
            grouping_result = grouper.group_files(scan_result.files)

        if progress_callback:
            progress_callback(100, "Processing completed!")

        return scan_result, grouping_result

    def _process_files_in_batches(
        self,
        files: list[AnimeFile],
        grouper: FileGrouper,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> GroupingResult:
        """Process files in batches to manage memory usage."""
        all_groups = []
        all_ungrouped = []
        total_errors = []

        for i in range(0, len(files), self.batch_size):
            batch = files[i : i + self.batch_size]

            if progress_callback:
                progress = 50 + int((i / len(files)) * 50)
                progress_callback(progress, f"Processing batch {i//self.batch_size + 1}...")

            # Process batch
            batch_result = grouper.group_files(batch)

            all_groups.extend(batch_result.groups)
            all_ungrouped.extend(batch_result.ungrouped_files)
            total_errors.extend(batch_result.errors)

            # Force garbage collection between batches
            gc.collect()

        # Merge similar groups across batches
        merged_groups = self._merge_groups_across_batches(all_groups)

        return GroupingResult(
            groups=merged_groups,
            ungrouped_files=all_ungrouped,
            grouping_duration=0.0,  # Will be calculated by caller
            total_files=len(files),
            grouped_files=sum(len(group.files) for group in merged_groups),
            similarity_threshold=self.similarity_threshold,
            errors=total_errors,
        )

    def _merge_groups_across_batches(self, groups: list[FileGroup]) -> list[FileGroup]:
        """Merge similar groups that were created across different batches."""
        if not groups:
            return groups

        merged_groups = []
        processed_groups = set()

        for i, group1 in enumerate(groups):
            if i in processed_groups:
                continue

            current_group = group1
            processed_groups.add(i)

            # Try to merge with other groups
            for j, group2 in enumerate(groups[i + 1 :], i + 1):
                if j in processed_groups:
                    continue

                if self._should_merge_groups(current_group, group2):
                    # Merge group2 into current_group
                    for file in group2.files:
                        current_group.add_file(file)
                    processed_groups.add(j)

            merged_groups.append(current_group)

        return merged_groups

    def _should_merge_groups(self, group1: FileGroup, group2: FileGroup) -> bool:
        """Check if two groups should be merged."""
        if not group1.files or not group2.files:
            return False

        # Use the best files from each group for comparison
        file1 = group1.best_file or group1.files[0]
        file2 = group2.best_file or group2.files[0]

        # Check filename similarity
        from difflib import SequenceMatcher

        similarity = SequenceMatcher(None, file1.filename, file2.filename).ratio()

        return similarity >= self.similarity_threshold


def optimize_worker_count(file_count: int, available_cores: int | None = None) -> int:
    """Calculate optimal worker count based on file count and system resources.

    Args:
        file_count: Number of files to process
        available_cores: Number of available CPU cores (auto-detect if None)

    Returns:
        Optimal number of worker threads
    """
    if available_cores is None:
        available_cores = psutil.cpu_count()

    # Base calculation on file count and available cores
    if file_count < 100:
        return min(2, available_cores)
    elif file_count < 1000:
        return min(4, available_cores)
    elif file_count < 10000:
        return min(8, available_cores)
    else:
        return min(16, available_cores)


def memory_efficient_scan(
    directory: Path,
    max_memory_mb: int = 500,
    progress_callback: Callable[[int, str], None] | None = None,
) -> ScanResult:
    """Memory-efficient file scanning that processes files in small batches.

    Args:
        directory: Directory to scan
        max_memory_mb: Maximum memory usage in MB
        progress_callback: Optional progress callback

    Returns:
        ScanResult with scanned files
    """
    # Calculate batch size based on available memory
    # available_memory = psutil.virtual_memory().available / (1024 * 1024)
    estimated_memory_per_file = 0.1  # MB per file (rough estimate)
    batch_size = max(10, int(max_memory_mb / estimated_memory_per_file))

    processor = OptimizedFileProcessor(
        max_workers=optimize_worker_count(1000),  # Estimate
        batch_size=batch_size,
        enable_caching=True,
    )

    scan_result, _ = processor.process_directory(directory, progress_callback)
    return scan_result
