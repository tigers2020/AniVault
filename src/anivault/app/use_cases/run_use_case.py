"""Run use case (Phase R4B).

Orchestrates the complete run workflow: scan → match → organize.
Shared by CLI run handler. app layer owns all step sequencing and
benchmark collection; CLI handler is responsible only for option
parsing, output rendering, and passing a pre-reset stats_collector.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from anivault.app.use_cases.match_use_case import MatchUseCase
from anivault.app.use_cases.organize_use_case import OrganizeUseCase
from anivault.app.use_cases.scan_use_case import ScanUseCase
from anivault.shared.constants import QueueConfig, WorkerConfig
from anivault.shared.constants.system import FileSystem
from anivault.shared.constants.file_formats import VideoFormats
from anivault.shared.types.cli import RunOptions

if TYPE_CHECKING:
    from anivault.core.statistics import StatisticsCollector

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Return-value contract
# ---------------------------------------------------------------------------


@dataclass
class RunStepResult:
    """Result of a single pipeline step."""

    step: str
    status: str  # "success" | "error" | "skipped"
    message: str
    exit_code: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunResult:
    """Aggregate result returned by RunUseCase.execute().

    Attributes:
        steps:     Ordered list of per-step outcomes.
        success:   True when every executed step succeeded.
        exit_code: 0 for success, non-zero on first failure.
        benchmark: Timing/throughput data when stats_collector was provided.
        message:   Optional human-readable summary or error message.
    """

    steps: list[RunStepResult] = field(default_factory=list)
    success: bool = True
    exit_code: int = 0
    benchmark: dict[str, object] | None = None
    message: str | None = None


# ---------------------------------------------------------------------------
# UseCase
# ---------------------------------------------------------------------------


class RunUseCase:
    """Orchestrate scan → match → organize pipeline.

    The caller (run_handler) is responsible for:
    - Parsing RunOptions from CLI args.
    - Providing a *reset* StatisticsCollector when benchmark mode is on.
    - Rendering output from the returned RunResult.

    This class must NOT call asyncio.run(); it is always an async coroutine
    so the event-loop boundary stays in the handler.
    """

    def __init__(
        self,
        scan_use_case: ScanUseCase,
        match_use_case: MatchUseCase,
        organize_use_case: OrganizeUseCase,
    ) -> None:
        self._scan = scan_use_case
        self._match = match_use_case
        self._organize = organize_use_case

    async def execute(
        self,
        options: RunOptions,
        directory: Path,
        stats_collector: StatisticsCollector | None = None,
    ) -> RunResult:
        """Run the full workflow according to *options*.

        Args:
            options:         Parsed RunOptions (CLI types; not re-assembled here).
            directory:       Resolved root directory.
            stats_collector: Optional pre-reset collector for benchmark timing.
                             The caller must call collector.reset() before
                             passing it in.

        Returns:
            RunResult with per-step outcomes and optional benchmark data.
        """
        result = RunResult()

        # ------------------------------------------------------------------
        # Step 1: Scan
        # ------------------------------------------------------------------
        if not options.skip_scan:
            step = self._run_scan_step(options, directory, stats_collector)
            result.steps.append(step)
            if step.status != "success":
                result.success = False
                result.exit_code = step.exit_code or 1
                result.message = step.message
                result.benchmark = _collect_benchmark(stats_collector, result.steps)
                return result
        else:
            result.steps.append(RunStepResult(step="scan", status="skipped", message="Scan step skipped"))

        # ------------------------------------------------------------------
        # Step 2: Match
        # ------------------------------------------------------------------
        if not options.skip_match:
            step = await self._run_match_step(directory, stats_collector)
            result.steps.append(step)
            if step.status != "success":
                result.success = False
                result.exit_code = step.exit_code or 1
                result.message = step.message
                result.benchmark = _collect_benchmark(stats_collector, result.steps)
                return result
        else:
            result.steps.append(RunStepResult(step="match", status="skipped", message="Match step skipped"))

        # ------------------------------------------------------------------
        # Step 3: Organize
        # ------------------------------------------------------------------
        if not options.skip_organize:
            step = self._run_organize_step(options, directory, stats_collector)
            result.steps.append(step)
            if step.status != "success":
                result.success = False
                result.exit_code = step.exit_code or 1
                result.message = step.message
                result.benchmark = _collect_benchmark(stats_collector, result.steps)
                return result
        else:
            result.steps.append(RunStepResult(step="organize", status="skipped", message="Organize step skipped"))

        result.benchmark = _collect_benchmark(stats_collector, result.steps)
        return result

    # ------------------------------------------------------------------
    # Private step runners
    # ------------------------------------------------------------------

    def _run_scan_step(
        self,
        options: RunOptions,
        directory: Path,
        stats_collector: StatisticsCollector | None,
    ) -> RunStepResult:
        """Execute the scan step (synchronous)."""
        _timing_start(stats_collector, "scan")
        try:
            self._scan.execute(
                directory=directory,
                extensions=list(options.extensions),
                num_workers=options.max_workers,
                max_queue_size=QueueConfig.DEFAULT_SIZE,
            )
            _timing_end(stats_collector, "scan")
            return RunStepResult(step="scan", status="success", message="Files scanned successfully")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            _timing_end(stats_collector, "scan")
            logger.exception("Error in scan step")
            return RunStepResult(step="scan", status="error", message=f"Scan step error: {exc}", exit_code=1)

    async def _run_match_step(
        self,
        directory: Path,
        stats_collector: StatisticsCollector | None,
    ) -> RunStepResult:
        """Execute the match step (async; no internal asyncio.run)."""
        _timing_start(stats_collector, "match")
        try:
            await self._match.execute(
                directory,
                extensions=tuple(FileSystem.CLI_VIDEO_EXTENSIONS),
                concurrency=4,
            )
            _timing_end(stats_collector, "match")
            return RunStepResult(step="match", status="success", message="Files matched successfully")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            _timing_end(stats_collector, "match")
            logger.exception("Error in match step")
            return RunStepResult(step="match", status="error", message=f"Match step error: {exc}", exit_code=1)

    def _run_organize_step(
        self,
        options: RunOptions,
        directory: Path,
        stats_collector: StatisticsCollector | None,
    ) -> RunStepResult:
        """Execute the organize step (synchronous)."""
        _timing_start(stats_collector, "organize")
        try:
            extensions_list = list(options.extensions)
            scanned_files = self._organize.scan(
                root_path=str(directory),
                extensions=extensions_list,
                num_workers=options.max_workers,
                max_queue_size=QueueConfig.DEFAULT_SIZE,
            )

            if not scanned_files:
                _timing_end(stats_collector, "organize")
                return RunStepResult(step="organize", status="success", message="No files to organize")

            if options.enhanced:
                destination = options.destination or "Anime"
                plan = self._organize.generate_enhanced_plan(scanned_files, destination=destination)
            else:
                plan = self._organize.generate_plan(scanned_files)

            if options.dry_run:
                _timing_end(stats_collector, "organize")
                return RunStepResult(
                    step="organize",
                    status="success",
                    message=f"Dry-run: {len(plan)} file operations planned",
                    extra={"dry_run": True, "plan_count": len(plan)},
                )

            results = self._organize.execute_plan(plan, directory)
            _timing_end(stats_collector, "organize")

            moved = sum(1 for r in results if r.success)
            return RunStepResult(
                step="organize",
                status="success",
                message=f"Files organized successfully ({moved}/{len(plan)} moved)",
                extra={"moved": moved, "total": len(plan)},
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            _timing_end(stats_collector, "organize")
            logger.exception("Error in organize step")
            return RunStepResult(step="organize", status="error", message=f"Organize step error: {exc}", exit_code=1)


# ---------------------------------------------------------------------------
# Benchmark helpers (no reference to global singleton)
# ---------------------------------------------------------------------------


def _timing_start(collector: StatisticsCollector | None, name: str) -> None:
    if collector is not None:
        collector.start_timing(name)


def _timing_end(collector: StatisticsCollector | None, name: str) -> None:
    if collector is not None:
        try:
            collector.end_timing(name)
        except Exception:  # pylint: disable=broad-exception-caught
            pass


def _collect_benchmark(
    collector: StatisticsCollector | None,
    steps: list[RunStepResult],
) -> dict[str, object] | None:
    """Build benchmark dict from collector state.  Returns None when no collector."""
    if collector is None:
        return None

    timers: dict[str, float] = {}
    for step in steps:
        name = step.step
        if name in collector.timers:
            timers[name] = collector.timers[name]

    total_time = sum(timers.values())
    total_files = collector.metrics.total_files
    files_per_second = total_files / total_time if total_time > 0 else 0.0

    return {
        "timers": timers,
        "total_time": total_time,
        "total_files": total_files,
        "files_per_second": files_per_second,
    }
