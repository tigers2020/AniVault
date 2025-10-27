"""Match command helper functions.

Extracted from match_handler.py for better code organization.
Contains core matching pipeline logic.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rich.console import Console

from anivault.cli.json_formatter import format_json_output
from anivault.cli.progress import create_progress_manager
from anivault.core.matching.engine import MatchingEngine
from anivault.core.parser.anitopy_parser import AnitopyParser
from anivault.services import (
    RateLimitStateMachine,
    SemaphoreManager,
    SQLiteCacheDB,
    TMDBClient,
    TokenBucketRateLimiter,
)
from anivault.shared.constants import FileSystem
from anivault.shared.constants.cli import CLIFormatting, CLIMessages


async def run_match_pipeline(
    options: Any,
    console: Console | None = None,
) -> int:
    """Run the complete matching pipeline.

    Args:
        options: Match command options
        console: Rich console (optional, created if None)

    Returns:
        Exit code (0 for success, 1 for error)
    """
    from rich.console import Console

    if console is None:
        console = Console()

    directory = _get_directory_from_options(options)
    _show_start_message(directory, options, console)

    services = _initialize_services()
    anime_files = _find_anime_files(directory)

    if not anime_files:
        return _handle_no_files_found(directory, options, console)

    _show_file_count(anime_files, options, console)
    processed_results = await _process_files(anime_files, services, options, console)
    _output_results(processed_results, directory, options, console)

    return 0


def _get_directory_from_options(options: Any) -> Path:
    """Extract directory path from options.

    Note: This function is now redundant. Use extract_directory_path from
    cli.common.path_utils instead for consistency.
    """
    from anivault.cli.common.path_utils import extract_directory_path

    return extract_directory_path(options.directory)


def _show_start_message(directory: Path, options: Any, console: Console) -> None:
    """Show start message."""
    if not options.json_output:
        console.print(
            CLIFormatting.format_colored_message(
                f"Matching anime files in: {directory}",
                "success",
            ),
        )


def _initialize_services() -> dict[str, Any]:
    """Initialize matching services."""
    cache_db_path = Path(FileSystem.CACHE_DIRECTORY) / "tmdb_cache.db"
    cache = SQLiteCacheDB(cache_db_path)
    rate_limiter = TokenBucketRateLimiter(capacity=50, refill_rate=50)
    semaphore_manager = SemaphoreManager(concurrency_limit=4)
    state_machine = RateLimitStateMachine()

    tmdb_client = TMDBClient(
        rate_limiter=rate_limiter,
        semaphore_manager=semaphore_manager,
        state_machine=state_machine,
    )

    matching_engine = MatchingEngine(tmdb_client=tmdb_client, cache=cache)
    parser = AnitopyParser()

    return {
        "cache": cache,
        "rate_limiter": rate_limiter,
        "semaphore_manager": semaphore_manager,
        "state_machine": state_machine,
        "tmdb_client": tmdb_client,
        "matching_engine": matching_engine,
        "parser": parser,
    }


def _find_anime_files(directory: Path) -> list[Path]:
    """Find anime files in directory."""
    anime_files: list[Path] = []
    for ext in FileSystem.CLI_VIDEO_EXTENSIONS:
        anime_files.extend(directory.rglob(f"*{ext}"))
    return anime_files


def _handle_no_files_found(
    directory: Path,
    options: Any,
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
    options: Any,
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


async def _process_files(
    anime_files: list[Path],
    services: dict[str, Any],
    options: Any,
    console: Console,
) -> list[dict[str, Any]]:
    """Process anime files concurrently."""
    parser = services["parser"]
    matching_engine = services["matching_engine"]
    progress_manager = create_progress_manager(disabled=options.json_output)

    results = []
    with progress_manager.spinner(CLIMessages.Info.SCANNING_FILES):
        semaphore = asyncio.Semaphore(4)

        async def process_with_semaphore(file_path: Path) -> dict[str, Any]:
            async with semaphore:
                return await process_file_for_matching(
                    file_path, parser, matching_engine, console
                )

        results = await asyncio.gather(
            *[process_with_semaphore(fp) for fp in anime_files],
            return_exceptions=True,
        )

    return _process_exceptions(results, anime_files, options, console)


def _process_exceptions(
    results: list[Any],
    anime_files: list[Path],
    options: Any,
    console: Console,
) -> list[dict[str, Any]]:
    """Process exceptions in results."""
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            if not options.json_output:
                console.print(
                    CLIFormatting.format_colored_message(
                        f"Error processing {anime_files[i]}: {result}",
                        "error",
                    ),
                )
            processed_results.append(
                {
                    "file_path": str(anime_files[i]),
                    "error": str(result),
                }
            )
        elif isinstance(result, dict):
            processed_results.append(result)
        else:
            processed_results.append(
                {
                    "file_path": str(anime_files[i]),
                    "error": "Unexpected result type",
                }
            )

    return processed_results


def _output_results(
    processed_results: list[dict[str, Any]],
    directory: Path,
    options: Any,
    console: Console,
) -> None:
    """Output match results."""
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


async def process_file_for_matching(
    file_path: Path,
    parser: AnitopyParser,
    matching_engine: MatchingEngine,
    console: Console,
) -> dict[str, Any]:
    """Process a single file through matching pipeline.

    Args:
        file_path: Path to anime file
        parser: Parser instance
        matching_engine: Matching engine instance
        console: Rich console

    Returns:
        Processing result dictionary
    """
    try:
        # Parse filename
        parsing_result = parser.parse(str(file_path))

        if not parsing_result:
            return {"file_path": str(file_path), "error": "Failed to parse filename"}

        # Convert to dict for matching
        if hasattr(parsing_result, "to_dict"):
            parsing_dict = parsing_result.to_dict()
        elif isinstance(parsing_result, dict):
            parsing_dict = parsing_result
        else:
            parsing_dict = {
                "anime_title": getattr(parsing_result, "title", ""),
                "episode_number": getattr(parsing_result, "episode", ""),
                "release_group": getattr(parsing_result, "release_group", ""),
                "video_resolution": getattr(parsing_result, "quality", ""),
            }

        # Match against TMDB
        match_result = await matching_engine.find_match(parsing_dict)
        match_result_dict = match_result.to_dict() if match_result else None

        return {
            "file_path": str(file_path),
            "parsing_result": parsing_result,
            "match_result": match_result_dict,
        }

    except Exception as e:  # noqa: BLE001
        return {"file_path": str(file_path), "error": str(e)}


def display_match_results(results: list[dict[str, Any]], console: Console) -> None:
    """Display match results in formatted table.

    Args:
        results: List of match results
        console: Rich console
    """
    from rich.table import Table

    if not results:
        console.print("[yellow]No results to display.[/yellow]")
        return

    table = Table(title="Anime File Match Results")
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Title", style="green")
    table.add_column("Episode", style="blue")
    table.add_column("Quality", style="magenta")
    table.add_column("TMDB Match", style="yellow")
    table.add_column("Confidence", style="red")

    for result in results:
        if "error" in result:
            table.add_row(
                result["file_path"],
                "Error",
                "-",
                "-",
                "Failed",
                "0.00",
            )
            continue

        parsing_result = result.get("parsing_result")
        match_result = result.get("match_result")

        if not parsing_result:
            continue

        title = parsing_result.title or "Unknown"
        episode = str(parsing_result.episode) if parsing_result.episode else "-"
        quality = parsing_result.quality or "-"

        if match_result and match_result.get("tmdb_data"):
            tmdb_data = match_result["tmdb_data"]
            tmdb_title = tmdb_data.get("title") or tmdb_data.get("name", "Unknown")
            confidence = f"{match_result.get('match_confidence', 0.0):.2f}"
        else:
            tmdb_title = "No match"
            confidence = "0.00"

        table.add_row(
            result["file_path"], title, episode, quality, tmdb_title, confidence
        )

    console.print(table)


def _calculate_success_rate(successful_matches: int, total_files: int) -> float:
    """Calculate success rate percentage.

    Args:
        successful_matches: Number of successful matches
        total_files: Total number of files

    Returns:
        Success rate as percentage (0-100)
    """
    if total_files == 0:
        return 0.0
    return (successful_matches / total_files) * 100


def collect_match_data(results: list[dict[str, Any]], directory: str) -> dict[str, Any]:
    """Collect match data for JSON output.

    Args:
        results: List of match results
        directory: Scanned directory

    Returns:
        Match statistics and file data
    """
    total_files = len(results)
    stats = _calculate_file_statistics(results)
    match_stats = _collect_matching_statistics(results)

    return {
        "match_summary": {
            "total_files": total_files,
            "successful_matches": match_stats["successful_matches"],
            "high_confidence_matches": match_stats["high_confidence"],
            "medium_confidence_matches": match_stats["medium_confidence"],
            "low_confidence_matches": match_stats["low_confidence"],
            "errors": match_stats["errors"],
            "total_size_bytes": stats["total_size"],
            "total_size_formatted": _format_size(stats["total_size"]),
            "scanned_directory": str(directory),
            "success_rate": _calculate_success_rate(
                match_stats["successful_matches"], total_files
            ),
        },
        "file_statistics": {
            "counts_by_extension": stats["file_counts"],
            "scanned_paths": stats["scanned_paths"],
        },
        "files": stats["file_data"],
    }


def _calculate_file_statistics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate file statistics from results."""
    total_size = 0
    file_counts: dict[str, int] = {}
    scanned_paths = []
    file_data = []

    for result in results:
        file_path = result.get("file_path", "Unknown")
        scanned_paths.append(file_path)

        file_size = _get_file_size(file_path)
        total_size += file_size

        file_ext = Path(file_path).suffix.lower()
        file_counts[file_ext] = file_counts.get(file_ext, 0) + 1

        file_info = _build_file_info(result, file_path, file_size, file_ext)
        file_data.append(file_info)

    return {
        "total_size": total_size,
        "file_counts": file_counts,
        "scanned_paths": scanned_paths,
        "file_data": file_data,
    }


def _get_file_size(file_path: str) -> int:
    """Get file size in bytes."""
    try:
        return Path(file_path).stat().st_size
    except (OSError, TypeError):
        return 0


def _build_file_info(
    result: dict[str, Any],
    file_path: str,
    file_size: int,
    file_ext: str,
) -> dict[str, Any]:
    """Build file information dictionary."""
    parsing_result = result.get("parsing_result")
    match_result = result.get("match_result")

    file_info = {
        "file_path": file_path,
        "file_name": Path(file_path).name,
        "file_size": file_size,
        "file_extension": file_ext,
    }

    if parsing_result:
        file_info["parsing_result"] = _extract_parsing_result(parsing_result)

    file_info["match_result"] = _extract_match_result(result, match_result)

    return file_info


def _extract_parsing_result(parsing_result: Any) -> dict[str, Any]:
    """Extract parsing result data."""
    return {
        "title": parsing_result.title,
        "episode": parsing_result.episode,
        "season": parsing_result.season,
        "quality": parsing_result.quality,
        "source": parsing_result.source,
        "codec": parsing_result.codec,
        "audio": parsing_result.audio,
        "release_group": parsing_result.release_group,
        "confidence": parsing_result.confidence,
        "parser_used": parsing_result.parser_used,
        "additional_info": asdict(parsing_result.additional_info)
        if hasattr(parsing_result, "additional_info")
        else {},
    }


def _extract_match_result(
    result: dict[str, Any],
    match_result: dict[str, Any] | None,
) -> dict[str, Any]:
    """Extract match result data."""
    if match_result:
        return {
            "match_confidence": match_result.get("match_confidence", 0.0),
            "tmdb_data": match_result.get("tmdb_data"),
            "enrichment_status": match_result.get("enrichment_status", "UNKNOWN"),
        }
    if "error" in result:
        return {
            "match_confidence": 0.0,
            "tmdb_data": None,
            "enrichment_status": "ERROR",
        }
    return {
        "match_confidence": 0.0,
        "tmdb_data": None,
        "enrichment_status": "NO_MATCH",
    }


def _collect_matching_statistics(results: list[dict[str, Any]]) -> dict[str, int]:
    """Collect matching statistics."""
    high_confidence_threshold = 0.8
    medium_confidence_threshold = 0.6

    successful_matches = 0
    high_confidence = 0
    medium_confidence = 0
    low_confidence = 0
    errors = 0

    for result in results:
        match_result = result.get("match_result")

        if match_result:
            successful_matches += 1
            conf = match_result.get("match_confidence", 0.0)

            if conf >= high_confidence_threshold:
                high_confidence += 1
            elif conf >= medium_confidence_threshold:
                medium_confidence += 1
            else:
                low_confidence += 1
        elif "error" in result:
            errors += 1

    return {
        "successful_matches": successful_matches,
        "high_confidence": high_confidence,
        "medium_confidence": medium_confidence,
        "low_confidence": low_confidence,
        "errors": errors,
    }


def _format_size(size_bytes: float) -> str:
    """Format size in human-readable format."""
    bytes_per_unit = 1024.0

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < bytes_per_unit:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= bytes_per_unit
    return f"{size_bytes:.1f} PB"
