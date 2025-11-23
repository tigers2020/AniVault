"""Match command helper functions.

Extracted from match_handler.py for better code organization.
Contains core matching pipeline logic.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

from dependency_injector.wiring import Provide, inject
from rich.console import Console
from rich.table import Table

from anivault.cli.common.path_utils import extract_directory_path
from anivault.cli.json_formatter import format_json_output
from anivault.cli.progress import create_progress_manager
from anivault.containers import Container
from anivault.core.matching.engine import MatchingEngine
from anivault.core.matching.models import MatchResult
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
from anivault.shared.errors import (
    AniVaultError,
    AniVaultParsingError,
    ErrorCode,
    ErrorContext,
)
from anivault.shared.metadata_models import FileMetadata
from anivault.utils.resource_path import get_project_root

logger = logging.getLogger(__name__)


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


@inject
def _initialize_services(
    matching_engine: MatchingEngine = Provide[Container.matching_engine],
) -> dict[str, Any]:
    """Initialize matching services.

    Args:
        matching_engine: MatchingEngine instance injected from DI container

    Returns:
        Dictionary containing initialized services
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
) -> list[FileMetadata]:
    """Process anime files concurrently.

    Args:
        anime_files: List of file paths to process
        services: Dictionary containing parser and matching_engine
        options: Match command options
        console: Rich console for output

    Returns:
        List of FileMetadata instances (None results are filtered out)
    """
    parser = services["parser"]
    matching_engine = services["matching_engine"]
    progress_manager = create_progress_manager(disabled=options.json_output)

    results = []
    with progress_manager.spinner(CLIMessages.Info.SCANNING_FILES):
        semaphore = asyncio.Semaphore(4)

        async def process_with_semaphore(file_path: Path) -> FileMetadata | None:
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
) -> list[FileMetadata]:
    """Process exceptions in results and convert to FileMetadata.

    Args:
        results: List of processing results (FileMetadata, None, or Exception)
        anime_files: List of file paths (for error reporting)
        options: Match command options
        console: Rich console for output

    Returns:
        List of FileMetadata instances (None and Exception results are converted
        to FileMetadata with error indication)
    """
    processed_results: list[FileMetadata] = []
    for i, result in enumerate(results):
        file_path = anime_files[i]

        if isinstance(result, Exception):
            if not options.json_output:
                console.print(
                    CLIFormatting.format_colored_message(
                        f"Error processing {file_path}: {result}",
                        "error",
                    ),
                )
            # Create FileMetadata with error indication

            error_parsing_result = ParsingResult(
                title=str(file_path.name),
                additional_info=ParsingAdditionalInfo(),
            )
            processed_results.append(
                _match_result_to_file_metadata(file_path, error_parsing_result, None)
            )
        elif isinstance(result, FileMetadata):
            processed_results.append(result)
        elif result is None:
            # Parsing failed - create FileMetadata with minimal info

            failed_parsing_result = ParsingResult(
                title=str(file_path.name),
                additional_info=ParsingAdditionalInfo(),
            )
            processed_results.append(
                _match_result_to_file_metadata(file_path, failed_parsing_result, None)
            )
        else:
            # Unexpected type - convert to FileMetadata
            if not options.json_output:
                console.print(
                    CLIFormatting.format_colored_message(
                        f"Unexpected result type for {file_path}",
                        "warning",
                    ),
                )

            unexpected_parsing_result = ParsingResult(
                title=str(file_path.name),
                additional_info=ParsingAdditionalInfo(),
            )
            processed_results.append(
                _match_result_to_file_metadata(
                    file_path, unexpected_parsing_result, None
                )
            )

    return processed_results


def _output_results(
    processed_results: list[FileMetadata],
    directory: Path,
    options: Any,
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


def _parsing_result_to_dict(
    parsing_result: ParsingResult | dict[str, Any] | Any,
) -> dict[str, Any]:
    """Convert ParsingResult to dict for matching engine.

    This helper function extracts the complex conditional logic from
    process_file_for_matching() to reduce cyclomatic complexity.

    Args:
        parsing_result: ParsingResult dataclass, dict, or any object with attributes

    Returns:
        Dictionary in format expected by MatchingEngine.find_match()

    Example:
        >>> result = ParsingResult(title="Attack on Titan", episode=1)
        >>> d = _parsing_result_to_dict(result)
        >>> d["anime_title"]
        'Attack on Titan'
    """
    if isinstance(parsing_result, dict):
        return parsing_result

    if isinstance(parsing_result, ParsingResult):
        return {
            "anime_title": parsing_result.title,
            "episode_number": parsing_result.episode,
            "release_group": parsing_result.release_group,
            "video_resolution": parsing_result.quality,
            "anime_year": parsing_result.year,
        }

    # Fallback for other types (backward compatibility)
    return {
        "anime_title": getattr(parsing_result, "title", ""),
        "episode_number": getattr(parsing_result, "episode", ""),
        "release_group": getattr(parsing_result, "release_group", ""),
        "video_resolution": getattr(parsing_result, "quality", ""),
    }


def _match_result_to_file_metadata(
    file_path: Path,
    parsing_result: ParsingResult,
    match_result: MatchResult | None,
) -> FileMetadata:
    """Convert MatchResult and ParsingResult to FileMetadata.

    This helper function combines parsing and matching results into
    a single FileMetadata dataclass for type-safe processing.

    Args:
        file_path: Path to the media file
        parsing_result: Parsed file information
        match_result: TMDB match result or None

    Returns:
        FileMetadata instance with combined data

    Example:
        >>> parsing = ParsingResult(title="AOT", episode=1)
        >>> match = MatchResult(tmdb_id=1429, title="Attack on Titan", ...)
        >>> metadata = _match_result_to_file_metadata(Path("/aot.mkv"), parsing, match)
        >>> metadata.tmdb_id
        1429
    """
    # Start with parsing result data
    title = parsing_result.title
    year = parsing_result.year
    season = parsing_result.season
    episode = parsing_result.episode

    # Initialize TMDB fields with defaults
    genres: list[str] = []
    overview: str | None = None
    poster_path: str | None = None
    vote_average: float | None = None
    tmdb_id: int | None = None
    media_type: str | None = None

    # Override with match result data if available
    if match_result is not None:
        title = match_result.title
        year = match_result.year or year
        tmdb_id = match_result.tmdb_id
        media_type = match_result.media_type
        poster_path = match_result.poster_path
        overview = match_result.overview
        vote_average = match_result.vote_average

    return FileMetadata(
        title=title,
        file_path=file_path,
        file_type=file_path.suffix.lstrip(".").lower(),
        year=year,
        season=season,
        episode=episode,
        genres=genres,
        overview=overview,
        poster_path=poster_path,
        vote_average=vote_average,
        tmdb_id=tmdb_id,
        media_type=media_type,
    )


async def process_file_for_matching(
    file_path: Path,
    parser: AnitopyParser,
    matching_engine: MatchingEngine,
    console: Console,
) -> FileMetadata | None:
    """Process a single file through matching pipeline.

    This function has been refactored to reduce cyclomatic complexity
    by extracting helper functions for parsing conversion and result transformation.

    Args:
        file_path: Path to anime file
        parser: Parser instance
        matching_engine: Matching engine instance
        console: Rich console (reserved for future error display)

    Returns:
        FileMetadata instance with match results, or None if parsing fails

    Example:
        >>> metadata = await process_file_for_matching(
        ...     Path("/anime/aot.mkv"), parser, engine, console
        ... )
        >>> metadata.tmdb_id if metadata else None
        1429
    """
    try:
        # Parse filename
        parsing_result = parser.parse(str(file_path))

        if not parsing_result:
            return None

        # Ensure ParsingResult type for conversion

        if isinstance(parsing_result, dict):
            parsing_result = ParsingResult(
                title=parsing_result.get("anime_title", ""),
                episode=parsing_result.get("episode_number"),
                season=parsing_result.get("season"),
                year=parsing_result.get("anime_year"),
                quality=parsing_result.get("video_resolution"),
                release_group=parsing_result.get("release_group"),
                additional_info=ParsingAdditionalInfo(),
            )
        elif not isinstance(parsing_result, ParsingResult):
            # For other types, create minimal ParsingResult
            # Note: This branch is reachable when parsing_result is neither dict nor ParsingResult
            parsing_result = ParsingResult(  # type: ignore[unreachable]
                title=getattr(parsing_result, "title", str(file_path.name)),
                episode=getattr(parsing_result, "episode", None),
                season=getattr(parsing_result, "season", None),
                year=getattr(parsing_result, "year", None),
                quality=getattr(parsing_result, "quality", None),
                release_group=getattr(parsing_result, "release_group", None),
                additional_info=ParsingAdditionalInfo(),
            )
        # At this point, parsing_result is guaranteed to be ParsingResult

        # Convert to dict for matching engine
        parsing_dict = _parsing_result_to_dict(parsing_result)

        # Match against TMDB
        match_result = await matching_engine.find_match(parsing_dict)

        # Convert to FileMetadata
        return _match_result_to_file_metadata(file_path, parsing_result, match_result)

    except (KeyError, ValueError, TypeError, AttributeError) as e:
        # Data structure access errors during file processing
        context = ErrorContext(
            file_path=str(file_path),
            operation="process_file_for_matching",
        )
        error = AniVaultParsingError(
            ErrorCode.DATA_PROCESSING_ERROR,
            f"Data parsing error processing file for matching: {e}",
            context,
            original_error=e,
        )
        logger.exception("Error processing file for matching: %s", error.message)
        # Return FileMetadata with error indication (tmdb_id=None)
        # This maintains type safety while indicating failure

        minimal_parsing_result = ParsingResult(
            title=str(file_path.name),
            additional_info=ParsingAdditionalInfo(),
        )
        return _match_result_to_file_metadata(file_path, minimal_parsing_result, None)
    except Exception as e:  # - Unexpected errors
        # Unexpected errors during file processing
        context = ErrorContext(
            file_path=str(file_path),
            operation="process_file_for_matching",
        )
        error = AniVaultError(
            ErrorCode.DATA_PROCESSING_ERROR,
            f"Unexpected error processing file for matching: {e}",
            context,
            original_error=e,
        )
        logger.exception("Error processing file for matching: %s", error.message)
        # Return FileMetadata with error indication (tmdb_id=None)
        # This maintains type safety while indicating failure

        minimal_parsing_result = ParsingResult(
            title=str(file_path.name),
            additional_info=ParsingAdditionalInfo(),
        )
        return _match_result_to_file_metadata(file_path, minimal_parsing_result, None)


def display_match_results(results: list[FileMetadata], console: Console) -> None:
    """Display match results in formatted table.

    Args:
        results: List of FileMetadata instances
        console: Rich console for output
    """
    if not results:
        console.print("[yellow]No results to display.[/yellow]")
        return

    table = Table(title="Anime File Match Results")
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Title", style="green")
    table.add_column("Episode", style="blue")
    table.add_column("TMDB Match", style="yellow")
    table.add_column("TMDB Rating", style="red")

    for metadata in results:
        file_name = metadata.file_path.name
        title = metadata.title or "Unknown"
        episode = str(metadata.episode) if metadata.episode else "-"

        if metadata.tmdb_id:
            tmdb_title = metadata.title or "Unknown"
            rating = f"{metadata.vote_average:.1f}" if metadata.vote_average else "N/A"
        else:
            tmdb_title = "No match"
            rating = "N/A"

        table.add_row(file_name, title, episode, tmdb_title, rating)

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


def collect_match_data(results: list[FileMetadata], directory: str) -> dict[str, Any]:
    """Collect match data for JSON output.

    Args:
        results: List of FileMetadata instances
        directory: Scanned directory path

    Returns:
        Match statistics and file data dictionary
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


def _calculate_file_statistics(results: list[FileMetadata]) -> dict[str, Any]:
    """Calculate file statistics from FileMetadata results.

    Args:
        results: List of FileMetadata instances

    Returns:
        Dictionary containing file statistics
    """
    total_size = 0
    file_counts: dict[str, int] = {}
    scanned_paths = []
    file_data = []

    for metadata in results:
        file_path = str(metadata.file_path)
        scanned_paths.append(file_path)

        file_size = _get_file_size(file_path)
        total_size += file_size

        file_ext = metadata.file_path.suffix.lower()
        file_counts[file_ext] = file_counts.get(file_ext, 0) + 1

        file_info = _build_file_info(metadata, file_path, file_size, file_ext)
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
    metadata: FileMetadata,
    file_path: str,
    file_size: int,
    file_ext: str,
) -> dict[str, Any]:
    """Build file information dictionary from FileMetadata.

    Args:
        metadata: FileMetadata instance
        file_path: File path string
        file_size: File size in bytes
        file_ext: File extension

    Returns:
        Dictionary with file information for JSON output
    """
    file_info = {
        "file_path": file_path,
        "file_name": Path(file_path).name,
        "file_size": file_size,
        "file_extension": file_ext,
        "title": metadata.title,
        "year": metadata.year,
        "season": metadata.season,
        "episode": metadata.episode,
    }

    # Add TMDB match information
    if metadata.tmdb_id:
        file_info["match_result"] = {
            "match_confidence": 1.0,  # FileMetadata indicates successful match
            "tmdb_data": {
                "id": metadata.tmdb_id,
                "title": metadata.title,
                "media_type": metadata.media_type,
                "poster_path": metadata.poster_path,
                "overview": metadata.overview,
                "vote_average": metadata.vote_average,
            },
            "enrichment_status": "SUCCESS",
        }
    else:
        file_info["match_result"] = {
            "match_confidence": 0.0,
            "tmdb_data": None,
            "enrichment_status": "NO_MATCH",
        }

    return file_info


def _collect_matching_statistics(results: list[FileMetadata]) -> dict[str, int]:
    """Collect matching statistics from FileMetadata results.

    Args:
        results: List of FileMetadata instances

    Returns:
        Dictionary with matching statistics
    """
    high_confidence_threshold = 0.8
    medium_confidence_threshold = 0.6

    successful_matches = 0
    high_confidence = 0
    medium_confidence = 0
    low_confidence = 0
    errors = 0

    for metadata in results:
        # Consider a match successful if tmdb_id is present
        if metadata.tmdb_id:
            successful_matches += 1
            # Use vote_average as proxy for confidence (if available)
            # Otherwise assume medium confidence for matched items
            conf = metadata.vote_average if metadata.vote_average else 0.7

            if conf >= high_confidence_threshold:
                high_confidence += 1
            elif conf >= medium_confidence_threshold:
                medium_confidence += 1
            else:
                low_confidence += 1
        else:
            # No match found (not necessarily an error)
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
