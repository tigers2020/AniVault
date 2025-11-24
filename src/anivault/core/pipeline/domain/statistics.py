"""Pipeline statistics formatting and aggregation.

This module provides utilities for formatting and aggregating pipeline statistics:
- format_statistics(): Format statistics into human-readable report
- StatisticsAggregator: Aggregate and export statistics in various formats
"""

from __future__ import annotations

import json
from typing import Any

from anivault.core.pipeline.utils import (
    ParserStatistics,
    QueueStatistics,
    ScanStatistics,
)


def format_statistics(
    scan_stats: ScanStatistics,
    queue_stats: QueueStatistics,
    parser_stats: ParserStatistics,
    total_duration: float,
) -> str:
    """Format pipeline statistics into a human-readable report.

    Args:
        scan_stats: ScanStatistics instance with scanning metrics.
        queue_stats: QueueStatistics instance with queue metrics.
        parser_stats: ParserStatistics instance with parser metrics.
        total_duration: Total pipeline execution time in seconds.

    Returns:
        A formatted multi-line string containing all statistics.
    """
    # Calculate success/failure percentages
    total_processed = parser_stats.items_processed
    success_rate = (parser_stats.successes / total_processed * 100) if total_processed > 0 else 0
    failure_rate = (parser_stats.failures / total_processed * 100) if total_processed > 0 else 0

    # Calculate cache hit/miss percentages
    total_cache_ops = parser_stats.cache_hits + parser_stats.cache_misses
    cache_hit_rate = (parser_stats.cache_hits / total_cache_ops * 100) if total_cache_ops > 0 else 0
    cache_miss_rate = (parser_stats.cache_misses / total_cache_ops * 100) if total_cache_ops > 0 else 0

    # Build the statistics report
    lines = [
        "",
        "=" * 60,
        "                    PIPELINE STATISTICS",
        "=" * 60,
        "",
        "Timing:",
        f"  - Total pipeline time:  {total_duration:.2f}s",
        "",
        "Scanner:",
        f"  - Files scanned:        {scan_stats.files_scanned:,}",
        f"  - Directories scanned:  {scan_stats.directories_scanned:,}",
        "",
        "Queue:",
        f"  - Items put:            {queue_stats.items_put:,}",
        f"  - Items got:            {queue_stats.items_got:,}",
        f"  - Peak size:            {queue_stats.max_size:,}",
        "",
        "Parser:",
        f"  - Items processed:      {parser_stats.items_processed:,}",
        f"  - Successful:           {parser_stats.successes:,} ({success_rate:.2f}%)",
        f"  - Failed:               {parser_stats.failures:,} ({failure_rate:.2f}%)",
        "",
        "Cache:",
        f"  - Cache hits:           {parser_stats.cache_hits:,} ({cache_hit_rate:.2f}%)",
        f"  - Cache misses:         {parser_stats.cache_misses:,} ({cache_miss_rate:.2f}%)",
        "",
        "=" * 60,
        "",
    ]

    return "\n".join(lines)


class StatisticsAggregator:
    """Aggregates and exports pipeline statistics in various formats.

    This class provides methods for collecting statistics from pipeline
    components and exporting them in different formats (dict, JSON, formatted text).
    """

    def __init__(
        self,
        scan_stats: ScanStatistics,
        queue_stats: QueueStatistics,
        parser_stats: ParserStatistics,
        total_duration: float,
    ) -> None:
        """Initialize the statistics aggregator.

        Args:
            scan_stats: ScanStatistics instance with scanning metrics.
            queue_stats: QueueStatistics instance with queue metrics.
            parser_stats: ParserStatistics instance with parser metrics.
            total_duration: Total pipeline execution time in seconds.
        """
        self.scan_stats = scan_stats
        self.queue_stats = queue_stats
        self.parser_stats = parser_stats
        self.total_duration = total_duration

    def aggregate(self) -> dict[str, Any]:
        """Aggregate all statistics into a structured dictionary.

        Returns:
            Dictionary containing all pipeline statistics organized by category.
        """
        # Calculate percentages
        total_processed = self.parser_stats.items_processed
        success_rate = (self.parser_stats.successes / total_processed * 100) if total_processed > 0 else 0.0
        failure_rate = (self.parser_stats.failures / total_processed * 100) if total_processed > 0 else 0.0

        total_cache_ops = self.parser_stats.cache_hits + self.parser_stats.cache_misses
        cache_hit_rate = (self.parser_stats.cache_hits / total_cache_ops * 100) if total_cache_ops > 0 else 0.0
        cache_miss_rate = (self.parser_stats.cache_misses / total_cache_ops * 100) if total_cache_ops > 0 else 0.0

        return {
            "timing": {
                "total_duration": self.total_duration,
                "total_duration_formatted": f"{self.total_duration:.2f}s",
            },
            "scanner": {
                "files_scanned": self.scan_stats.files_scanned,
                "directories_scanned": self.scan_stats.directories_scanned,
            },
            "queue": {
                "items_put": self.queue_stats.items_put,
                "items_got": self.queue_stats.items_got,
                "max_size": self.queue_stats.max_size,
            },
            "parser": {
                "items_processed": self.parser_stats.items_processed,
                "successes": self.parser_stats.successes,
                "failures": self.parser_stats.failures,
                "success_rate": success_rate,
                "failure_rate": failure_rate,
            },
            "cache": {
                "cache_hits": self.parser_stats.cache_hits,
                "cache_misses": self.parser_stats.cache_misses,
                "cache_hit_rate": cache_hit_rate,
                "cache_miss_rate": cache_miss_rate,
            },
        }

    def to_dict(self) -> dict[str, Any]:
        """Export statistics as a dictionary.

        Returns:
            Dictionary containing all pipeline statistics.
        """
        return self.aggregate()

    def to_json(self, indent: int = 2) -> str:
        """Export statistics as a JSON string.

        Args:
            indent: Number of spaces for JSON indentation (default: 2).

        Returns:
            JSON-formatted string containing all pipeline statistics.
        """
        return json.dumps(self.aggregate(), indent=indent, ensure_ascii=False)

    def format_report(self) -> str:
        """Format statistics using the standard format_statistics function.

        Returns:
            Human-readable formatted statistics report.
        """
        return format_statistics(
            scan_stats=self.scan_stats,
            queue_stats=self.queue_stats,
            parser_stats=self.parser_stats,
            total_duration=self.total_duration,
        )
