"""Run use case (Phase R4B).

Orchestrates the complete run workflow: scan → match → organize.
Shared by CLI run handler. app layer owns all step sequencing and
benchmark collection; CLI handler is responsible only for option
parsing, output rendering, and passing a pre-reset stats_collector.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from anivault.application.use_cases.match_use_case import MatchUseCase
from anivault.application.use_cases.organize_use_case import OrganizeUseCase
from anivault.application.use_cases.scan_use_case import ScanUseCase
from anivault.shared.constants import QueueConfig
from anivault.shared.constants.system import FileSystem
from anivault.domain.entities.metadata import FileMetadata
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
    status: StepStatus
    message: str
    exit_code: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


class StepStatus(StrEnum):
    """Allowed status values for run steps."""

    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"


STEP_FAILURE_EXIT_CODES: dict[str, int] = {
    # Phase 3 contract hardening: keep current behavior explicit.
    "scan": 1,
    "match": 1,
    "organize": 1,
}


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
        benchmark: bool = False,
        *,
        stats_collector: StatisticsCollector | None = None,
    ) -> RunResult:
        """Run the full workflow according to *options*.

        R5: ``benchmark`` flag replaces the caller-side ``stats_collector``
        parameter so run_handler never imports from anivault.core directly.
        When ``benchmark=True`` the use case obtains and resets the global
        StatisticsCollector internally.

        The legacy ``stats_collector`` keyword argument is kept for backward
        compatibility in tests; it takes precedence over ``benchmark`` when
        provided explicitly.

        Args:
            options:         Parsed RunOptions (CLI types; not re-assembled here).
            directory:       Resolved root directory.
            benchmark:       Enable benchmark timing (obtains & resets collector).
            stats_collector: Deprecated — pass a pre-reset collector directly.
                             Overrides ``benchmark`` when not None.

        Returns:
            RunResult with per-step outcomes and optional benchmark data.
        """
        if stats_collector is None and benchmark:
            from anivault.core.statistics import get_statistics_collector

            stats_collector = get_statistics_collector()
            stats_collector.reset()

        result = RunResult()
        scanned: list[FileMetadata] | None = None
        matched: list[FileMetadata] | None = None

        # ------------------------------------------------------------------
        # Step 1: Scan
        # ------------------------------------------------------------------
        if not options.skip_scan:
            step, scanned = self._run_scan_step(options, directory, stats_collector)
            if not _append_step(result, step, stats_collector):
                return result
        else:
            result.steps.append(RunStepResult(step="scan", status=StepStatus.SKIPPED, message="Scan step skipped"))

        # ------------------------------------------------------------------
        # Step 2: Match
        # ------------------------------------------------------------------
        if not options.skip_match:
            step, matched = await self._run_match_step(
                directory,
                stats_collector,
                scanned_files=scanned,
            )
            if not _append_step(result, step, stats_collector):
                return result
        else:
            result.steps.append(RunStepResult(step="match", status=StepStatus.SKIPPED, message="Match step skipped"))

        # ------------------------------------------------------------------
        # Step 3: Organize
        # ------------------------------------------------------------------
        if not options.skip_organize:
            organize_files = _pick_organize_files(matched, scanned)
            step = self._run_organize_step(
                options,
                directory,
                stats_collector,
                organize_files=organize_files,
            )
            if not _append_step(result, step, stats_collector):
                return result
        else:
            result.steps.append(RunStepResult(step="organize", status=StepStatus.SKIPPED, message="Organize step skipped"))

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
    ) -> tuple[RunStepResult, list[FileMetadata] | None]:
        """Execute the scan step (synchronous)."""
        _timing_start(stats_collector, "scan")
        try:
            scanned_files = self._scan.execute(
                directory=directory,
                extensions=list(options.extensions),
                num_workers=options.max_workers,
                max_queue_size=QueueConfig.DEFAULT_SIZE,
            )
            _timing_end(stats_collector, "scan")
            return (
                RunStepResult(step="scan", status=StepStatus.SUCCESS, message="Files scanned successfully"),
                scanned_files,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            _timing_end(stats_collector, "scan")
            logger.exception("Error in scan step")
            return (
                RunStepResult(
                    step="scan",
                    status=StepStatus.ERROR,
                    message=f"Scan step error: {exc}",
                    exit_code=STEP_FAILURE_EXIT_CODES["scan"],
                ),
                None,
            )

    async def _run_match_step(
        self,
        directory: Path,
        stats_collector: StatisticsCollector | None,
        *,
        scanned_files: list[FileMetadata] | None,
    ) -> tuple[RunStepResult, list[FileMetadata] | None]:
        """Execute the match step (async; no internal asyncio.run)."""
        _timing_start(stats_collector, "match")
        try:
            matched_files: list[FileMetadata]
            if scanned_files is not None:
                matched_files = await self._match.execute_from_files(scanned_files)
            else:
                matched_files = await self._match.execute(
                    directory,
                    extensions=tuple(FileSystem.CLI_VIDEO_EXTENSIONS),
                    concurrency=4,
                )
            _timing_end(stats_collector, "match")
            return (
                RunStepResult(step="match", status=StepStatus.SUCCESS, message="Files matched successfully"),
                matched_files,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            _timing_end(stats_collector, "match")
            logger.exception("Error in match step")
            return (
                RunStepResult(
                    step="match",
                    status=StepStatus.ERROR,
                    message=f"Match step error: {exc}",
                    exit_code=STEP_FAILURE_EXIT_CODES["match"],
                ),
                None,
            )

    def _build_organize_plan(
        self,
        options: RunOptions,
        directory: Path,
        organize_files: list[FileMetadata] | None,
    ) -> list | None:
        """Build the organize plan from artifact files or via fallback scan.

        Returns a plan list, or None when there are no files to organize.
        The fallback scan path is taken only when organize_files is None
        (i.e. both skip_scan and skip_match were set by the caller).
        """
        if organize_files is None:
            scanned_files = self._organize.scan(
                root_path=str(directory),
                extensions=list(options.extensions),
                num_workers=options.max_workers,
                max_queue_size=QueueConfig.DEFAULT_SIZE,
            )
            if not scanned_files:
                return None
            if options.enhanced:
                return self._organize.generate_enhanced_plan(scanned_files, destination=options.destination or "Anime")
            return self._organize.generate_plan(scanned_files)

        if not organize_files:
            return None

        if options.enhanced:
            return self._organize.generate_enhanced_plan_from_metadata(organize_files, destination=options.destination or "Anime")
        return self._organize.generate_plan_from_metadata(organize_files)

    def _run_organize_step(
        self,
        options: RunOptions,
        directory: Path,
        stats_collector: StatisticsCollector | None,
        *,
        organize_files: list[FileMetadata] | None,
    ) -> RunStepResult:
        """Execute the organize step (synchronous)."""
        _timing_start(stats_collector, "organize")
        try:
            plan = self._build_organize_plan(options, directory, organize_files)
            if plan is None:
                _timing_end(stats_collector, "organize")
                return RunStepResult(
                    step="organize",
                    status=StepStatus.SUCCESS,
                    message="No files to organize",
                    extra={"dry_run": False, "plan_count": 0, "moved": 0, "total": 0},
                )

            if options.dry_run:
                _timing_end(stats_collector, "organize")
                return RunStepResult(
                    step="organize",
                    status=StepStatus.SUCCESS,
                    message=f"Dry-run: {len(plan)} file operations planned",
                    extra={"dry_run": True, "plan_count": len(plan), "moved": 0, "total": len(plan)},
                )

            results = self._organize.execute_plan(plan, directory)
            _timing_end(stats_collector, "organize")

            moved = sum(1 for r in results if r.success)
            return RunStepResult(
                step="organize",
                status=StepStatus.SUCCESS,
                message=f"Files organized successfully ({moved}/{len(plan)} moved)",
                extra={
                    "dry_run": False,
                    "plan_count": len(plan),
                    "moved": moved,
                    "total": len(plan),
                },
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            _timing_end(stats_collector, "organize")
            logger.exception("Error in organize step")
            return RunStepResult(
                step="organize",
                status=StepStatus.ERROR,
                message=f"Organize step error: {exc}",
                exit_code=STEP_FAILURE_EXIT_CODES["organize"],
            )


# ---------------------------------------------------------------------------
# Module-level step helpers
# ---------------------------------------------------------------------------


def _pick_organize_files(
    matched: list[FileMetadata] | None,
    scanned: list[FileMetadata] | None,
) -> list[FileMetadata] | None:
    """Select the best artifact list for the organize step.

    Priority: matched (even when empty) → scanned → None.
    ``matched is None`` means match was skipped, so scanned is the fallback.
    An empty ``matched`` (no API results) intentionally keeps the empty list.
    """
    return matched if matched is not None else scanned


def _append_step(
    result: RunResult,
    step: RunStepResult,
    collector: StatisticsCollector | None,
) -> bool:
    """Append *step* to *result* and return True when the pipeline may continue.

    On failure the result is marked unsuccessful and benchmark data is
    collected so the caller can return immediately.
    """
    result.steps.append(step)
    if step.status is not StepStatus.SUCCESS:
        result.success = False
        result.exit_code = step.exit_code
        result.message = step.message
        result.benchmark = _collect_benchmark(collector, result.steps)
        return False
    return True


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
        except Exception:  # pylint: disable=broad-exception-caught  # noqa: BLE001
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
