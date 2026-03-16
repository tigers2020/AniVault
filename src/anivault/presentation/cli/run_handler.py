"""Run command handler for AniVault CLI.

Orchestration entry point: Container → RunUseCase → output helpers.
This handler is responsible for option parsing, output rendering, and
passing a pre-reset StatisticsCollector when benchmark mode is active.
RunUseCase owns all step sequencing (scan → match → organize).
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

import typer
from dependency_injector.wiring import Provide, inject
from rich.console import Console

from anivault.application.use_cases.run_use_case import RunResult, RunUseCase, StepStatus
from anivault.presentation.cli.common.context import get_cli_context
from anivault.presentation.cli.common.error_decorator import handle_cli_errors
from anivault.presentation.cli.common.path_utils import extract_directory_path
from anivault.presentation.cli.common.setup_decorator import setup_handler
from anivault.presentation.cli.json_formatter import format_json_output
from anivault.infrastructure.composition import Container
from anivault.shared.constants import CLI, CLIDefaults
from anivault.shared.constants.cli import CLIFormatting, CLIMessages
from anivault.shared.types.cli import CLIDirectoryPath, RunOptions

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


@inject
async def _execute_run(
    options: RunOptions,
    directory: Path,
    *,
    is_benchmark: bool = False,
    use_case: RunUseCase = Provide[Container.run_use_case],
) -> RunResult:
    """Acquire RunUseCase from container and execute.

    R5: benchmark collector acquisition moved to RunUseCase.execute() so this
    handler never imports from anivault.core (statistics) directly.
    """
    return await use_case.execute(options, directory, benchmark=is_benchmark)


def _build_run_data(options: RunOptions, directory: Path) -> dict[str, Any]:
    """Build initial run_data for workflow tracking."""
    return {
        "workflow_summary": {
            CLIMessages.StatusKeys.DIRECTORY: str(directory),
            "extensions": options.extensions,
            "dry_run": options.dry_run,
            "skip_scan": options.skip_scan,
            "skip_match": options.skip_match,
            "skip_organize": options.skip_organize,
            "max_workers": options.max_workers,
            "batch_size": options.batch_size,
        },
        "steps": [],
    }


def _run_result_to_steps(result: RunResult) -> list[dict[str, Any]]:
    """Convert RunResult.steps to the steps list-of-dict format for CLI output."""
    return [
        {
            CLIMessages.StatusKeys.STEP: s.step,
            CLIMessages.StatusKeys.STATUS: s.status.value,
            "message": s.message,
            **({"exit_code": s.exit_code} if s.exit_code else {}),
            "extra": s.extra,
        }
        for s in result.steps
    ]


def _display_benchmark_results(
    benchmark: dict[str, object],
    console: Console,
    is_json_output: bool,
    run_data: dict[str, Any],
) -> None:
    """Display benchmark results with timing and throughput."""
    run_data["benchmark"] = benchmark

    if is_json_output:
        return

    timers = benchmark.get("timers", {})
    total_time = benchmark.get("total_time", 0.0)
    total_files = benchmark.get("total_files", 0)
    files_per_second = benchmark.get("files_per_second", 0.0)

    console.print("\n[bold cyan]Benchmark Results:[/bold cyan]")
    console.print("\n[bold]Step Timings:[/bold]")
    for step_name, duration in (timers or {}).items():
        console.print(f"  {step_name.title()}: {duration:.3f}s")

    console.print(f"\n[bold]Total Time:[/bold] {total_time:.3f}s")
    console.print(f"[bold]Total Files:[/bold] {total_files}")
    console.print(f"[bold]Throughput:[/bold] {files_per_second:.2f} files/second")


def _emit_run_success(
    run_data: dict[str, Any],
    console: Console,
    is_json_output: bool,
) -> None:
    """Emit success output (JSON or console message + summary)."""
    if is_json_output:
        json_output = format_json_output(
            success=True,
            command=CLIMessages.CommandNames.RUN,
            data=run_data,
        )
        sys.stdout.buffer.write(json_output)
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
    else:
        console.print(
            CLIFormatting.format_colored_message(
                "\n✓ Run workflow completed successfully!",
                "success",
            )
        )
        _print_run_summary(run_data, console)


def _print_run_summary(run_data: dict[str, Any], console: Console) -> None:
    """Print workflow summary."""
    console.print("\n[bold]Workflow Summary:[/bold]")

    workflow_summary = run_data["workflow_summary"]
    console.print(f"  Directory: {workflow_summary['directory']}")
    console.print(f"  Extensions: {', '.join(workflow_summary['extensions'])}")
    console.print(f"  Dry Run: {workflow_summary['dry_run']}")
    console.print(f"  Max Workers: {workflow_summary['max_workers']}")
    console.print(f"  Batch Size: {workflow_summary['batch_size']}")

    console.print("\n[bold]Steps Completed:[/bold]")
    for step in run_data["steps"]:
        step_status = StepStatus(step["status"])
        if step_status is StepStatus.SUCCESS:
            status_icon, status_color = "✓", "green"
        elif step_status is StepStatus.SKIPPED:
            status_icon, status_color = "⊘", "dim"
        else:
            status_icon, status_color = "✗", "red"
        console.print(f"  {status_icon} {step['step'].title()}: [{status_color}]{step_status.value}[/{status_color}]" f" - {step['message']}")


def _output_json_error(error_message: str, run_data: dict[str, Any]) -> None:
    """Output JSON error."""
    json_output = format_json_output(
        success=False,
        command="run",
        errors=[error_message],
        data=run_data,
    )
    sys.stdout.buffer.write(json_output)
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()


# ---------------------------------------------------------------------------
# Command entry point
# ---------------------------------------------------------------------------


@setup_handler(requires_directory=True, supports_json=True, allow_dry_run=True)
@handle_cli_errors(operation="handle_run", command_name="run")
def handle_run_command(options: RunOptions, **kwargs: Any) -> int:
    """Handle the run command which orchestrates scan, match, and organize.

    Args:
        options: Validated run command options
        **kwargs: Injected by decorators (console, logger_adapter)

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    console: Console = kwargs.get("console") or Console()
    logger_adapter = kwargs.get("logger_adapter", logger)

    logger_adapter.info(CLI.INFO_COMMAND_STARTED.format(command=CLIMessages.CommandNames.RUN))

    directory = extract_directory_path(options.directory)
    context = get_cli_context()
    is_json_output = bool(context and context.is_json_output_enabled())
    is_benchmark = bool(context and context.is_benchmark_enabled())

    run_data = _build_run_data(options, directory)

    # Single event-loop boundary: asyncio.run lives here and nowhere else.
    result: RunResult = asyncio.run(_execute_run(options, directory, is_benchmark=is_benchmark))

    # Populate steps in run_data
    run_data["steps"] = _run_result_to_steps(result)

    if not result.success:
        error_message = result.message or f"Run workflow failed (exit code {result.exit_code})"
        if is_json_output:
            _output_json_error(error_message, run_data)
        else:
            logger_adapter.error(error_message)
        return result.exit_code or CLIDefaults.EXIT_ERROR

    # Benchmark output (benchmark data already included in result)
    if is_benchmark and result.benchmark:
        _display_benchmark_results(result.benchmark, console, is_json_output, run_data)

    _emit_run_success(run_data, console, is_json_output)
    logger_adapter.info(CLI.INFO_COMMAND_COMPLETED.format(command=CLIMessages.CommandNames.RUN))
    return CLIDefaults.EXIT_SUCCESS


def run_command(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    directory: Path = typer.Argument(
        ...,
        help="Directory containing anime files to process",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    recursive: bool = typer.Option(
        True,
        "--recursive/--no-recursive",
        "-r",
        help="Process files recursively in subdirectories",
    ),
    include_subtitles: bool = typer.Option(
        True,
        "--include-subtitles/--no-include-subtitles",
        help="Include subtitle files in processing",
    ),
    include_metadata: bool = typer.Option(
        True,
        "--include-metadata/--no-include-metadata",
        help="Include metadata files in processing",
    ),
    output_file: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file for processing results (JSON format)",
        writable=True,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be processed without actually processing files",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompts and proceed with processing",
    ),
    json: bool = typer.Option(
        False,
        "--json",
        help="Output results in JSON format",
    ),
) -> None:
    """Run the complete anime organization workflow (scan, match, organize).

    This command orchestrates the entire AniVault workflow in sequence:
    1. Scan directory for anime files and extract metadata
    2. Match files against TMDB database for accurate identification
    3. Organize files into structured directory layout

    Workflow phases:
    - Phase 1 (Scan): Discover and parse anime files using anitopy
    - Phase 2 (Match): Correlate parsed data with TMDB database
    - Phase 3 (Organize): Create organized directory structure

    Benefits of using 'run' vs individual commands:
    - Single command for complete workflow
    - Consistent options across all phases
    - Unified error handling and progress tracking

    Examples:
        # Run complete workflow on current directory
        anivault run .

        # Run with specific options and save results
        anivault run /path/to/anime --recursive --output workflow_results.json

        # Preview what would be processed without making changes
        anivault run . --dry-run

        # Run without confirmation prompts (automated mode)
        anivault run . --yes

        # Run with verbose output to see each phase
        anivault run /path/to/anime --verbose

        # Run with custom file extensions
        anivault run /path/to/anime --extensions "mkv,mp4"

        # Run and output results in JSON format
        anivault run /path/to/anime --json
    """
    try:
        context = get_cli_context()

        run_options = RunOptions(
            directory=CLIDirectoryPath(path=directory),
            recursive=recursive,
            include_subtitles=include_subtitles,
            include_metadata=include_metadata,
            dry_run=dry_run,
            yes=yes,
            json_output=bool(json),
            verbose=context.verbose if context else 0,
            output=output_file,
        )

        exit_code = handle_run_command(run_options)

        if exit_code != CLIDefaults.EXIT_SUCCESS:
            raise typer.Exit(exit_code)

    except ValueError as e:
        logger.exception("Validation error")
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(CLIDefaults.EXIT_ERROR) from e
