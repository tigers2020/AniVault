"""Scan command helper functions.

This module contains the core business logic for the scan command,
extracted for better maintainability and reusability.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rich.console import Console

from anivault.cli.progress import create_progress_manager
from anivault.core.pipeline.main import run_pipeline
from anivault.services import (
    RateLimitStateMachine,
    SemaphoreManager,
    TMDBClient,
    TokenBucketRateLimiter,
)

# Import MetadataEnricher conditionally to avoid import errors
try:
    from anivault.services import MetadataEnricher
except ImportError:
    MetadataEnricher = None
from anivault.shared.constants import CLIDefaults, QueueConfig
from anivault.shared.constants.file_formats import VideoFormats
from anivault.shared.metadata_models import FileMetadata

logger = logging.getLogger(__name__)


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
        "title": metadata.title,
        "file_path": str(metadata.file_path),
        "file_name": metadata.file_name,
        "file_type": metadata.file_type,
        "year": metadata.year,
        "season": metadata.season,
        "episode": metadata.episode,
        "genres": metadata.genres,
        "overview": metadata.overview,
        "poster_path": metadata.poster_path,
        "vote_average": metadata.vote_average,
        "tmdb_id": metadata.tmdb_id,
        "media_type": metadata.media_type,
    }


def run_scan_pipeline(
    directory: Path,
    console: Console,
    *,
    is_json_output: bool = False,
) -> list[dict[str, Any]]:
    """Run the file scanning pipeline.

    Args:
        directory: Directory to scan
        console: Rich console for output
        is_json_output: Whether JSON output is enabled

    Returns:
        List of scan results

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
        from anivault.shared.constants import CLIFormatting

        console.print(
            CLIFormatting.format_colored_message(
                "✅ File scanning completed!",
                "success",
            )
        )

    return file_results


async def enrich_metadata(
    file_results: list[dict[str, Any]],
    console: Console,
    *,
    is_json_output: bool = False,
) -> list[dict[str, Any]]:
    """Enrich file results with TMDB metadata.

    Args:
        file_results: List of file scan results
        console: Rich console for output
        is_json_output: Whether JSON output is enabled

    Returns:
        List of enriched results
    """
    # Extract parsing results
    parsing_results = []
    for result in file_results:
        if "parsing_result" in result:
            parsing_results.append(result["parsing_result"])

    if not parsing_results:
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

    # Enrich metadata
    enriched_results = []
    for parsing_result in progress_manager.track(
        parsing_results,
        "Enriching metadata...",
    ):
        enriched = await enricher.enrich_metadata(parsing_result)
        enriched_results.append(enriched)

    # Combine enriched metadata with original results
    enriched_file_results = []
    for original_result, enriched_metadata in zip(
        file_results,
        enriched_results,
    ):
        enriched_result = original_result.copy()
        enriched_result["enriched_metadata"] = enriched_metadata
        enriched_file_results.append(enriched_result)

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
        "other_info": parsing_result.other_info,
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
    results: list[dict[str, Any]],
    directory: Path,
    *,
    show_tmdb: bool = True,
) -> dict[str, Any]:
    """Collect scan data for JSON output.

    Args:
        results: List of scan results
        directory: Scanned directory path
        show_tmdb: Whether TMDB metadata was enriched

    Returns:
        Dictionary containing scan statistics and file data
    """
    from anivault.shared.constants.cli import CLIMessages

    # Calculate basic statistics
    total_files = len(results)
    total_size = CLIDefaults.DEFAULT_FILE_SIZE
    file_counts_by_extension: dict[str, int] = {}
    scanned_paths = []

    # Process each result
    file_data = []
    for result in results:
        file_path = result.get(
            CLIMessages.Output.FILE_PATH_KEY,
            CLIMessages.Output.UNKNOWN_VALUE,
        )
        parsing_result = result.get("parsing_result")
        enriched_metadata = result.get("enriched_metadata")

        # Add to scanned paths
        scanned_paths.append(file_path)

        # Calculate file size
        try:
            file_size = Path(file_path).stat().st_size
            total_size += file_size
        except (OSError, TypeError):
            file_size = CLIDefaults.DEFAULT_FILE_SIZE

        # Count by extension
        file_ext = Path(file_path).suffix.lower()
        file_counts_by_extension[file_ext] = (
            file_counts_by_extension.get(file_ext, 0) + 1
        )

        # Prepare file data
        file_info = {
            "file_path": file_path,
            "file_name": Path(file_path).name,
            "file_size": file_size,
            "file_extension": file_ext,
        }

        # Add parsing result if available
        if parsing_result:
            file_info["parsing_result"] = _extract_parsing_result_dict(parsing_result)

        # Add enriched metadata if available
        if show_tmdb and enriched_metadata:
            file_info["enriched_metadata"] = _extract_enriched_metadata_dict(
                enriched_metadata
            )

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
    results: list[dict[str, Any]],
    console: Console,
    *,
    show_tmdb: bool = True,
) -> None:
    """Display scan results in a formatted table.

    Args:
        results: List of scan results
        console: Rich console for output
        show_tmdb: Whether to show TMDB metadata
    """
    from rich.table import Table

    from anivault.shared.constants.cli import CLIMessages

    if not results:
        console.print("[yellow]No files found.[/yellow]")
        return

    # Create results table
    table = Table(title="Anime File Scan Results")
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Title", style="green")
    table.add_column("Episode", style="blue")
    table.add_column("Quality", style="magenta")

    if show_tmdb:
        table.add_column("TMDB Match", style="yellow")
        table.add_column("TMDB Rating", style="red")
        table.add_column("Status", style="green")

    for result in results:
        file_path = result.get(
            CLIMessages.Output.FILE_PATH_KEY,
            CLIMessages.Output.UNKNOWN_VALUE,
        )
        parsing_result = result.get("parsing_result")
        enriched_metadata = result.get("enriched_metadata")

        if not parsing_result:
            continue

        # Basic file info
        title = parsing_result.title or "Unknown"
        episode = str(parsing_result.episode) if parsing_result.episode else "-"
        quality = parsing_result.quality or "-"

        if show_tmdb and enriched_metadata:
            # TMDB info
            tmdb_data = enriched_metadata.tmdb_data
            if tmdb_data:
                tmdb_title = tmdb_data.get("title") or tmdb_data.get("name", "Unknown")
                rating = tmdb_data.get("vote_average", "N/A")
                if isinstance(rating, (int, float)):
                    rating = f"{rating:.1f}"
            else:
                tmdb_title = "No match"
                rating = "N/A"

            status = enriched_metadata.enrichment_status
            confidence = f"{enriched_metadata.match_confidence:.2f}"

            table.add_row(
                Path(file_path).name,
                title,
                episode,
                quality,
                f"{tmdb_title} ({confidence})",
                str(rating),
                status,
            )
        else:
            table.add_row(Path(file_path).name, title, episode, quality)

    console.print(table)
