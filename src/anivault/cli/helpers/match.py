"""Match command helper functions.

Extracted from match_handler.py for better code organization.
Contains core matching pipeline logic.
"""

# pylint: disable=import-error  # dependency_injector is an optional dependency

from __future__ import annotations

import logging
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from dependency_injector.wiring import (  # pylint: disable=import-error
    Provide,
    inject,
)
from rich.console import Console

from anivault.app.use_cases.match_use_case import MatchUseCase
from anivault.cli.common.path_utils import extract_directory_path
from anivault.cli.json_formatter import format_json_output
from anivault.cli.models.match_services import MatchServices
from anivault.cli.progress import create_progress_manager
from anivault.containers import Container
from anivault.core.matching.engine import MatchingEngine
from anivault.core.matching.models import MatchResult
from anivault.core.matching.pipeline import (
    MatchOptions as PipelineMatchOptions,
)
from anivault.core.matching.pipeline import (
    MatchResultBundle,
    match_result_to_file_metadata,
    parsing_result_to_dict,
)
from anivault.core.matching.pipeline import (
    process_file_for_matching as _process_file_for_matching,
)
from anivault.core.parser.anitopy_parser import AnitopyParser
from anivault.core.parser.models import ParsingAdditionalInfo, ParsingResult
from anivault.services import (
    RateLimitStateMachine,
    SemaphoreManager,
    SQLiteCacheDB,
    TMDBClient,
    TokenBucketRateLimiter,
)
from anivault.shared.constants import FileSystem
from anivault.shared.constants.cli import CLIFormatting, CLIMessages
from anivault.shared.models.metadata import FileMetadata
from anivault.shared.types.cli import MatchOptions as CliMatchOptions
from anivault.utils.resource_path import get_project_root

from .match_formatters import collect_match_data, display_match_results

logger = logging.getLogger(__name__)


async def process_file_for_matching(
    file_path: Path,
    *args: object,
    engine: MatchingEngine | None = None,
    parser: AnitopyParser | None = None,
    options: PipelineMatchOptions | None = None,
    **kwargs: object,
) -> MatchResultBundle | FileMetadata | None:
    """Compatibility wrapper for process_file_for_matching."""
    legacy_signature = bool(args) and parser is None and engine is None
    if args and parser is None and engine is None:
        parser = cast("AnitopyParser | None", args[0] if len(args) > 0 else None)
        engine = cast("MatchingEngine | None", args[1] if len(args) > 1 else None)
    parser = parser or cast("AnitopyParser | None", kwargs.get("parser"))
    engine = engine or cast("MatchingEngine | None", kwargs.get("engine"))
    if parser is None or engine is None:
        raise TypeError("process_file_for_matching requires parser and engine")
    try:
        bundle = await _process_file_for_matching(
            file_path,
            engine=engine,
            parser=parser,
            options=options or PipelineMatchOptions(),
        )
    except Exception:
        if legacy_signature:
            error_parsing_result = ParsingResult(
                title=str(file_path.name),
                additional_info=ParsingAdditionalInfo(),
            )
            return match_result_to_file_metadata(file_path, error_parsing_result, None)
        raise
    return bundle.metadata if legacy_signature else bundle


def _parsing_result_to_dict(
    parsing_result: ParsingResult | Mapping[str, object] | object,
) -> dict[str, object]:
    """Convert parsing result to dict for compatibility tests.

    Args:
        parsing_result: ParsingResult or dict-like object

    Returns:
        Dictionary representation of parsing result
    """
    if isinstance(parsing_result, dict):
        return parsing_result
    if isinstance(parsing_result, ParsingResult):
        match_query = parsing_result_to_dict(parsing_result)
        return {
            "anime_title": match_query.anime_title,
            "episode_number": _coerce_int(match_query.episode),
            "season": _coerce_int(match_query.season),
            "anime_year": match_query.year,
            "video_resolution": match_query.video_resolution,
            "release_group": match_query.release_group,
        }
    return {
        "anime_title": getattr(parsing_result, "title", None),
        "episode_number": _coerce_int(getattr(parsing_result, "episode", None)),
        "season": _coerce_int(getattr(parsing_result, "season", None)),
        "anime_year": _coerce_int(getattr(parsing_result, "year", None)),
        "video_resolution": getattr(parsing_result, "quality", None),
        "release_group": getattr(parsing_result, "release_group", None),
    }


def _match_result_to_file_metadata(
    file_path: Path,
    parsing_result: ParsingResult,
    match_result: MatchResult | None,
) -> FileMetadata:
    """Convert match result to FileMetadata (compat wrapper)."""
    return match_result_to_file_metadata(file_path, parsing_result, match_result)


def _coerce_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


async def run_match_pipeline(
    options: CliMatchOptions,
    console: Console | None = None,
) -> int:
    """Run the complete matching pipeline.

    Args:
        options: Match command options
        console: Rich console (optional, created if None)

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if console is None:
        console = Console()

    directory = _get_directory_from_options(options)
    _show_start_message(directory, options, console)

    services = _initialize_services()
    anime_files = _find_anime_files(directory)

    if not anime_files:
        return _handle_no_files_found(directory, options, console)

    _show_file_count(anime_files, options, console)
    use_case = MatchUseCase(services)
    progress_manager = create_progress_manager(disabled=options.json_output)
    with progress_manager.spinner(CLIMessages.Info.SCANNING_FILES):
        processed_results = await use_case.execute(
            directory,
            extensions=FileSystem.CLI_VIDEO_EXTENSIONS,
            concurrency=4,
        )
    _output_results(processed_results, directory, options, console)

    return 0


def _get_directory_from_options(options: CliMatchOptions) -> Path:
    """Extract directory path from options.

    Note: This function is now redundant. Use extract_directory_path from
    cli.common.path_utils instead for consistency.
    """
    return extract_directory_path(options.directory)


def _show_start_message(directory: Path, options: CliMatchOptions, console: Console) -> None:
    """Show start message."""
    if not options.json_output:
        console.print(
            CLIFormatting.format_colored_message(
                f"Matching anime files in: {directory}",
                "success",
            ),
        )


@inject
def _initialize_services(
    matching_engine: MatchingEngine = Provide[Container.matching_engine],
) -> MatchServices:
    """Initialize matching services.

    Args:
        matching_engine: MatchingEngine instance injected from DI container

    Returns:
        MatchServices container with initialized services
    """
    # Use centralized project root utility for consistent path resolution
    project_root = get_project_root()
    cache_db_path = project_root / FileSystem.CACHE_DIRECTORY / "tmdb_cache.db"
    cache = SQLiteCacheDB(cache_db_path)
    rate_limiter = TokenBucketRateLimiter(capacity=50, refill_rate=50)
    semaphore_manager = SemaphoreManager(concurrency_limit=4)
    state_machine = RateLimitStateMachine()

    tmdb_client = TMDBClient(
        rate_limiter=rate_limiter,
        semaphore_manager=semaphore_manager,
        state_machine=state_machine,
    )

    parser = AnitopyParser()

    return MatchServices(
        cache=cache,
        rate_limiter=rate_limiter,
        semaphore_manager=semaphore_manager,
        state_machine=state_machine,
        tmdb_client=tmdb_client,
        matching_engine=matching_engine,
        parser=parser,
    )


def _find_anime_files(directory: Path) -> list[Path]:
    """Find anime files in directory."""
    anime_files: list[Path] = []
    for ext in FileSystem.CLI_VIDEO_EXTENSIONS:
        anime_files.extend(directory.rglob(f"*{ext}"))
    return anime_files


def _handle_no_files_found(
    directory: Path,
    options: CliMatchOptions,
    console: Console,
) -> int:
    """Handle case when no anime files are found."""
    if options.json_output:
        match_data = collect_match_data([], str(directory))
        json_output = format_json_output(
            success=True,
            command=CLIMessages.CommandNames.MATCH,
            data=match_data,
            warnings=[CLIMessages.Info.NO_ANIME_FILES_FOUND],
        )
        sys.stdout.buffer.write(json_output)
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
    else:
        console.print(
            CLIFormatting.format_colored_message(
                CLIMessages.Info.NO_ANIME_FILES_FOUND,
                "warning",
            ),
        )
    return 0


def _show_file_count(
    anime_files: list[Path],
    options: CliMatchOptions,
    console: Console,
) -> None:
    """Show file count message."""
    if not options.json_output:
        console.print(
            CLIFormatting.format_colored_message(
                f"Found {len(anime_files)} anime files",
                "info",
            ),
        )


def _output_results(
    processed_results: list[FileMetadata],
    directory: Path,
    options: CliMatchOptions,
    console: Console,
) -> None:
    """Output match results.

    Args:
        processed_results: List of FileMetadata instances
        directory: Scanned directory path
        options: Match command options
        console: Rich console for output
    """
    if options.json_output:
        match_data = collect_match_data(processed_results, str(directory))
        json_output = format_json_output(
            success=True,
            command=CLIMessages.CommandNames.MATCH,
            data=match_data,
        )
        sys.stdout.buffer.write(json_output)
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
    else:
        display_match_results(processed_results, console)
