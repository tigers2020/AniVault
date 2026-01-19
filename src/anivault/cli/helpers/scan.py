"""Scan command helper functions.

This module contains the core business logic for the scan command,
extracted for better maintainability and reusability.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import TYPE_CHECKING

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
from anivault.shared.constants.scan_fields import ScanColors, ScanMessages
from anivault.shared.models.metadata import FileMetadata
from anivault.shared.types.metadata_types import FileMetadataDict, ParsingResultDict
from anivault.shared.utils.metadata_converter import MetadataConverter

logger = logging.getLogger(__name__)


def _dict_to_file_metadata(result: FileMetadataDict) -> FileMetadata:
    """Convert FileMetadataDict to FileMetadata for compatibility.

    Args:
        result: FileMetadataDict containing file metadata

    Returns:
        FileMetadata instance with converted data
    """
    return MetadataConverter.from_dict(result)


def _file_metadata_to_dict(metadata: FileMetadata) -> FileMetadataDict:
    """Convert FileMetadata dataclass to JSON-serializable dict.

    This helper function converts a FileMetadata instance to a dictionary
    suitable for JSON output using MetadataConverter, maintaining backward
    compatibility with existing CLI JSON output format.

    Args:
        metadata: FileMetadata instance to convert

    Returns:
        FileMetadataDict (JSON-serializable dictionary)

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
    return MetadataConverter.to_dict(metadata)


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
        file_results = run_pipeline(
            root_path=str(directory),
            extensions=list(VideoFormats.ALL_EXTENSIONS),
            num_workers=CLIDefaults.DEFAULT_WORKER_COUNT,
            max_queue_size=QueueConfig.DEFAULT_SIZE,
        )

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


def _extract_parsing_result_dict(parsing_result: ParsingResult) -> ParsingResultDict:
    """Extract parsing result as dictionary.

    This function converts a ParsingResult instance to its TypedDict representation
    using MetadataConverter for type safety.

    Args:
        parsing_result: ParsingResult instance to convert

    Returns:
        ParsingResultDict with parsing result data
    """
    return MetadataConverter.parsing_result_to_dict(parsing_result)


def _extract_enriched_metadata_dict(enriched_metadata: object) -> dict[str, object]:
    """Extract enriched metadata as dictionary.

    Note: This function is kept for backward compatibility but may be deprecated
    in favor of direct EnrichedMetadata model usage.

    Args:
        enriched_metadata: Enriched metadata object

    Returns:
        Dictionary with enriched metadata
    """
    # Type-safe access with fallback for backward compatibility
    if hasattr(enriched_metadata, "enrichment_status"):
        return {
            "enrichment_status": enriched_metadata.enrichment_status,
            "match_confidence": getattr(enriched_metadata, "match_confidence", None),
            "tmdb_data": getattr(enriched_metadata, "tmdb_data", None),
        }
    # Fallback for dict-like objects
    if isinstance(enriched_metadata, dict):
        return dict(enriched_metadata)
    # Fallback: convert to dict using asdict if dataclass
    if is_dataclass(enriched_metadata):
        return asdict(enriched_metadata)  # type: ignore[arg-type]
    return {}


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
) -> dict[str, object]:
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
