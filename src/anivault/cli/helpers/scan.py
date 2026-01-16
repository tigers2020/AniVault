"""Scan command helper functions.

This module contains the core business logic for the scan command,
extracted for better maintainability and reusability.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rich.console import Console

from rich.console import Console
from rich.table import Table

from anivault.cli.progress import create_progress_manager
from anivault.core.parser.models import ParsingAdditionalInfo, ParsingResult
from anivault.core.pipeline import run_pipeline
from anivault.services import RateLimitStateMachine, SemaphoreManager, TMDBClient, TokenBucketRateLimiter
from anivault.services.enricher import MetadataEnricher
from anivault.shared.constants import CLIDefaults, CLIFormatting, QueueConfig
from anivault.shared.constants.file_formats import VideoFormats
from anivault.shared.constants.scan_fields import ScanColors, ScanFields, ScanMessages
from anivault.shared.metadata_models import FileMetadata

logger = logging.getLogger(__name__)


def _dict_to_file_metadata(result: dict[str, Any]) -> FileMetadata:
    """Convert orchestrator dict result to FileMetadata.

    This function converts the dictionary structure returned by run_pipeline()
    (via orchestrator._file_metadata_to_dict) back to a type-safe FileMetadata
    dataclass instance.

    Args:
        result: Dictionary containing file metadata with keys:
            - file_path: str (required)
            - file_name: str (optional, used for file_name property)
            - title: str (required)
            - file_type: str (required)
            - file_extension: str (optional, ignored)
            - year: int | None (optional)
            - season: int | None (optional)
            - episode: int | None (optional)
            - genres: list[str] (optional)
            - overview: str | None (optional)
            - poster_path: str | None (optional)
            - vote_average: float | None (optional)
            - tmdb_id: int | None (optional)
            - media_type: str | None (optional)
            - status: str (optional, ignored)

    Returns:
        FileMetadata instance with converted data

    Raises:
        ValueError: If required fields are missing or invalid
        KeyError: If required keys are missing from result dict

    Example:
        >>> result_dict = {
        ...     "file_path": "/anime/aot.mkv",
        ...     "title": "Attack on Titan",
        ...     "file_type": "mkv",
        ...     "tmdb_id": 1429,
        ... }
        >>> metadata = _dict_to_file_metadata(result_dict)
        >>> isinstance(metadata, FileMetadata)
        True
    """
    file_path_str = result.get("file_path")
    if not file_path_str:
        msg = "file_path is required in result dictionary"
        raise ValueError(msg)

    file_path = Path(file_path_str)

    title = result.get("title")
    if not title:
        msg = "title is required in result dictionary"
        raise ValueError(msg)

    file_type = result.get("file_type")
    if not file_type:
        msg = "file_type is required in result dictionary"
        raise ValueError(msg)

    return FileMetadata(
        title=title,
        file_path=file_path,
        file_type=file_type,
        year=result.get("year"),
        season=result.get("season"),
        episode=result.get("episode"),
        genres=result.get("genres", []),
        overview=result.get("overview"),
        poster_path=result.get("poster_path"),
        vote_average=result.get("vote_average"),
        tmdb_id=result.get("tmdb_id"),
        media_type=result.get("media_type"),
    )


def _file_metadata_to_dict(metadata: FileMetadata) -> dict[str, Any]:
    """Convert FileMetadata dataclass to JSON-serializable dict.

    This helper function converts a FileMetadata instance to a dictionary
    suitable for JSON output, maintaining backward compatibility with
    existing CLI JSON output format.

    TODO(Task 3-5): Replace with ModelConverter.to_dict() after FileMetadata
    is migrated to Pydantic BaseTypeModel. This manual conversion will be
    obsolete once type migration is complete.

    Args:
        metadata: FileMetadata instance to convert

    Returns:
        JSON-serializable dictionary

    Example:
        >>> metadata = FileMetadata(
        ...     title="Attack on Titan",
        ...     file_path=Path("/anime/aot.mkv"),
        ...     file_type="mkv",
        ...     tmdb_id=1429,
        ... )
        >>> result = _file_metadata_to_dict(metadata)
        >>> isinstance(result, dict)
        True
    """
    return {
        ScanFields.TITLE: metadata.title,
        ScanFields.FILE_PATH: str(metadata.file_path),
        ScanFields.FILE_NAME: metadata.file_name,
        ScanFields.FILE_TYPE: metadata.file_type,
        ScanFields.YEAR: metadata.year,
        ScanFields.SEASON: metadata.season,
        ScanFields.EPISODE: metadata.episode,
        ScanFields.GENRES: metadata.genres,
        ScanFields.OVERVIEW: metadata.overview,
        ScanFields.POSTER_PATH: metadata.poster_path,
        ScanFields.VOTE_AVERAGE: metadata.vote_average,
        ScanFields.TMDB_ID: metadata.tmdb_id,
        ScanFields.MEDIA_TYPE: metadata.media_type,
    }


def run_scan_pipeline(
    directory: Path,
    console: Console,
    *,
    is_json_output: bool = False,
) -> list[FileMetadata]:
    """Run the file scanning pipeline.

    Args:
        directory: Directory to scan
        console: Rich console for output
        is_json_output: Whether JSON output is enabled

    Returns:
        List of FileMetadata instances containing scan results

    Raises:
        OSError: File system errors
        ValueError: Data processing errors
    """
    # Create progress manager (disabled for JSON output)
    progress_manager = create_progress_manager(disabled=is_json_output)

    # Run the file processing pipeline with progress display
    with progress_manager.spinner("Scanning files..."):
        file_results_dict = run_pipeline(
            root_path=str(directory),
            extensions=list(VideoFormats.ALL_EXTENSIONS),
            num_workers=CLIDefaults.DEFAULT_WORKER_COUNT,
            max_queue_size=QueueConfig.DEFAULT_SIZE,
        )

    # Convert dict results to FileMetadata instances
    file_results: list[FileMetadata] = []
    for result_dict in file_results_dict:
        try:
            file_metadata = _dict_to_file_metadata(result_dict)
            file_results.append(file_metadata)
        except (ValueError, KeyError) as e:
            logger.warning(
                "Failed to convert scan result to FileMetadata: %s",
                e,
                extra={"result_dict": result_dict},
            )
            # Skip invalid results but continue processing

    if not is_json_output and file_results:
        console.print(
            CLIFormatting.format_colored_message(
                ScanMessages.SCAN_COMPLETED,
                "success",
            )
        )

    return file_results


def _file_metadata_to_parsing_result(metadata: FileMetadata) -> ParsingResult:
    """Convert FileMetadata to ParsingResult for enrichment.

    This helper function reconstructs a ParsingResult from FileMetadata.
    Note that some fields (quality, source, codec, audio, release_group)
    are not available in FileMetadata and will be set to None.

    Args:
        metadata: FileMetadata instance to convert

    Returns:
        ParsingResult instance for enrichment
    """
    additional_info = ParsingAdditionalInfo()
    return ParsingResult(
        title=metadata.title,
        episode=metadata.episode,
        season=metadata.season,
        year=metadata.year,
        quality=None,  # Not available in FileMetadata
        source=None,  # Not available in FileMetadata
        codec=None,  # Not available in FileMetadata
        audio=None,  # Not available in FileMetadata
        release_group=None,  # Not available in FileMetadata
        confidence=1.0,  # Assume high confidence for converted data
        parser_used="file_metadata_converter",
        additional_info=additional_info,
    )


async def enrich_metadata(
    file_results: list[FileMetadata],
    _console: Console,  # Reserved for future use
    *,
    is_json_output: bool = False,
) -> list[FileMetadata]:
    """Enrich file results with TMDB metadata.

    Args:
        file_results: List of FileMetadata instances to enrich
        _console: Rich console for output (reserved for future use)  # pylint: disable=unused-argument  # noqa: ARG002
        is_json_output: Whether JSON output is enabled

    Returns:
        List of enriched FileMetadata instances
    """
    if not file_results:
        return file_results

    # Initialize TMDB client
    rate_limiter = TokenBucketRateLimiter(
        capacity=10,  # Default rate limit
        refill_rate=10,  # Default refill rate
    )
    semaphore_manager = SemaphoreManager(
        concurrency_limit=CLIDefaults.DEFAULT_SCAN_CONCURRENCY,
    )
    state_machine = RateLimitStateMachine()

    tmdb_client = TMDBClient(
        rate_limiter=rate_limiter,
        semaphore_manager=semaphore_manager,
        state_machine=state_machine,
    )

    enricher = MetadataEnricher(tmdb_client=tmdb_client)

    # Create progress manager (disabled for JSON output)
    progress_manager = create_progress_manager(disabled=is_json_output)

    # Convert FileMetadata to ParsingResult for enrichment
    parsing_results = [_file_metadata_to_parsing_result(metadata) for metadata in file_results]

    # Enrich metadata
    enriched_metadata_list = []
    for parsing_result in progress_manager.track(
        parsing_results,
        "Enriching metadata...",
    ):
        enriched = await enricher.enrich_metadata(parsing_result)
        enriched_metadata_list.append(enriched)

    # Convert EnrichedMetadata back to FileMetadata
    enriched_file_results = []
    for metadata, enriched in zip(file_results, enriched_metadata_list):
        # Use EnrichedMetadata.to_file_metadata() to convert
        enriched_file_metadata = enriched.to_file_metadata(metadata.file_path)
        enriched_file_results.append(enriched_file_metadata)

    return enriched_file_results


def _extract_parsing_result_dict(parsing_result: Any) -> dict[str, Any]:
    """Extract parsing result as dictionary.

    Args:
        parsing_result: Parsing result object

    Returns:
        Dictionary with parsing result data
    """
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
        "additional_info": (asdict(parsing_result.additional_info) if hasattr(parsing_result, "additional_info") else {}),
    }


def _extract_enriched_metadata_dict(enriched_metadata: Any) -> dict[str, Any]:
    """Extract enriched metadata as dictionary.

    Args:
        enriched_metadata: Enriched metadata object

    Returns:
        Dictionary with enriched metadata
    """
    return {
        "enrichment_status": enriched_metadata.enrichment_status,
        "match_confidence": enriched_metadata.match_confidence,
        "tmdb_data": enriched_metadata.tmdb_data,
    }


def _format_size_human_readable(size_bytes: float) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string (e.g., "1.5 GB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < CLIDefaults.BYTES_PER_KB:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= CLIDefaults.BYTES_PER_KB
    return f"{size_bytes:.1f} PB"


def collect_scan_data(
    results: list[FileMetadata],
    directory: Path,
    *,
    show_tmdb: bool = True,
) -> dict[str, Any]:
    """Collect scan data for JSON output.

    Args:
        results: List of FileMetadata instances
        directory: Scanned directory path
        show_tmdb: Whether TMDB metadata was enriched

    Returns:
        Dictionary containing scan statistics and file data
    """
    # Calculate basic statistics
    total_files = len(results)
    total_size = CLIDefaults.DEFAULT_FILE_SIZE
    file_counts_by_extension: dict[str, int] = {}
    scanned_paths = []

    # Process each result
    file_data = []
    for metadata in results:
        file_path = str(metadata.file_path)
        scanned_paths.append(file_path)

        # Calculate file size
        try:
            file_size = metadata.file_path.stat().st_size
            total_size += file_size
        except (OSError, TypeError):
            file_size = CLIDefaults.DEFAULT_FILE_SIZE

        # Count by extension
        file_ext = metadata.file_path.suffix.lower()
        file_counts_by_extension[file_ext] = file_counts_by_extension.get(file_ext, 0) + 1

        # Prepare file data from FileMetadata
        file_info = {
            "file_path": file_path,
            "file_name": metadata.file_name,
            "file_size": file_size,
            "file_extension": file_ext,
            "title": metadata.title,
            "year": metadata.year,
            "season": metadata.season,
            "episode": metadata.episode,
        }

        # Add TMDB metadata if available
        if show_tmdb and metadata.tmdb_id:
            file_info["tmdb_id"] = metadata.tmdb_id
            file_info["tmdb_title"] = metadata.title
            file_info["tmdb_rating"] = metadata.vote_average
            file_info["tmdb_genres"] = metadata.genres
            file_info["tmdb_overview"] = metadata.overview
            file_info["tmdb_poster_path"] = metadata.poster_path
            file_info["tmdb_media_type"] = metadata.media_type

        file_data.append(file_info)

    return {
        "scan_summary": {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_formatted": _format_size_human_readable(total_size),
            "scanned_directory": str(directory),
            "metadata_enriched": show_tmdb,
        },
        "file_statistics": {
            "counts_by_extension": file_counts_by_extension,
            "scanned_paths": scanned_paths,
        },
        "files": file_data,
    }


def display_scan_results(
    results: list[FileMetadata],
    console: Console,
    *,
    show_tmdb: bool = True,
) -> None:
    """Display scan results in a formatted table.

    Args:
        results: List of FileMetadata instances
        console: Rich console for output
        show_tmdb: Whether to show TMDB metadata
    """
    if not results:
        console.print(f"[{ScanColors.YELLOW}]No files found.[/{ScanColors.YELLOW}]")
        return

    # Create results table
    table = Table(title="Anime File Scan Results")
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Title", style="green")
    table.add_column("Episode", style=ScanColors.BLUE)
    table.add_column("Year", style="magenta")

    if show_tmdb:
        table.add_column("TMDB Match", style=ScanColors.YELLOW)
        table.add_column("TMDB Rating", style="red")
        table.add_column("Status", style="green")

    for metadata in results:
        file_path = str(metadata.file_path)
        title = metadata.title or "Unknown"
        episode = str(metadata.episode) if metadata.episode else "-"
        year = str(metadata.year) if metadata.year else "-"

        if show_tmdb and metadata.tmdb_id:
            # TMDB info
            tmdb_title = metadata.title or "Unknown"
            rating = f"{metadata.vote_average:.1f}" if metadata.vote_average else "N/A"
            status = "Matched" if metadata.tmdb_id else "No match"

            table.add_row(
                Path(file_path).name,
                title,
                episode,
                year,
                tmdb_title,
                str(rating),
                status,
            )
        else:
            table.add_row(Path(file_path).name, title, episode, year)

    console.print(table)
