"""Pipeline domain logic package.

This package contains domain-specific logic for the pipeline:
- lifecycle: Component lifecycle management functions
- orchestrator: Pipeline component factory and orchestration
- statistics: Statistics formatting and aggregation
"""

from __future__ import annotations

from anivault.core.pipeline.domain.lifecycle import (
    force_shutdown_if_needed,
    graceful_shutdown,
    signal_collector_shutdown,
    signal_parser_shutdown,
    start_pipeline_components,
    wait_for_collector_completion,
    wait_for_parser_completion,
    wait_for_scanner_completion,
)
from anivault.core.pipeline.domain.orchestrator import PipelineFactory, run_pipeline
from anivault.core.pipeline.domain.statistics import (
    StatisticsAggregator,
    format_statistics,
)

__all__ = [
    "PipelineFactory",
    "StatisticsAggregator",
    "force_shutdown_if_needed",
    "format_statistics",
    "graceful_shutdown",
    "run_pipeline",
    "signal_collector_shutdown",
    "signal_parser_shutdown",
    "start_pipeline_components",
    "wait_for_collector_completion",
    "wait_for_parser_completion",
    "wait_for_scanner_completion",
]
