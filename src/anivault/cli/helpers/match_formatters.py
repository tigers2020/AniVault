"""Match command formatting and statistics helpers.

Extracted from match.py for better code organization.
Functions for table display and JSON data collection.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from anivault.shared.models.metadata import FileMetadata
from anivault.shared.types.match_types import (
    FileStatisticsInternalDict,
    MatchDataDict,
    MatchFileInfoDict,
    MatchStatisticsDict,
)

from .format_utils import format_size, get_file_size


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


def collect_match_data(results: list[FileMetadata], directory: str) -> MatchDataDict:
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
            "total_size_formatted": format_size(stats["total_size"]),
            "scanned_directory": str(directory),
            "success_rate": _calculate_success_rate(match_stats["successful_matches"], total_files),
        },
        "file_statistics": {
            "counts_by_extension": stats["file_counts"],
            "scanned_paths": stats["scanned_paths"],
        },
        "files": stats["file_data"],
    }


def _calculate_success_rate(successful_matches: int, total_files: int) -> float:
    """Calculate success rate percentage."""
    if total_files == 0:
        return 0.0
    return (successful_matches / total_files) * 100


def _calculate_file_statistics(results: list[FileMetadata]) -> FileStatisticsInternalDict:
    """Calculate file statistics from FileMetadata results."""
    total_size = 0
    file_counts: dict[str, int] = {}
    scanned_paths: list[str] = []
    file_data: list[MatchFileInfoDict] = []

    for metadata in results:
        file_path = str(metadata.file_path)
        scanned_paths.append(file_path)

        file_size = get_file_size(file_path)
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


def _build_file_info(
    metadata: FileMetadata,
    file_path: str,
    file_size: int,
    file_ext: str,
) -> MatchFileInfoDict:
    """Build file information dictionary from FileMetadata."""
    file_info: MatchFileInfoDict = {
        "file_path": file_path,
        "file_name": Path(file_path).name,
        "file_size": file_size,
        "file_extension": file_ext,
        "title": metadata.title,
        "year": metadata.year,
        "season": metadata.season,
        "episode": metadata.episode,
        "match_result": {
            "match_confidence": 0.0,
            "tmdb_data": None,
            "enrichment_status": "NO_MATCH",
        },
    }

    if metadata.tmdb_id:
        file_info["match_result"] = {
            "match_confidence": 1.0,
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
    return file_info


def _collect_matching_statistics(results: list[FileMetadata]) -> MatchStatisticsDict:
    """Collect matching statistics from FileMetadata results."""
    high_confidence_threshold = 0.8
    medium_confidence_threshold = 0.6

    successful_matches = 0
    high_confidence = 0
    medium_confidence = 0
    low_confidence = 0
    errors = 0

    for metadata in results:
        if metadata.tmdb_id:
            successful_matches += 1
            conf = metadata.vote_average if metadata.vote_average else 0.7

            if conf >= high_confidence_threshold:
                high_confidence += 1
            elif conf >= medium_confidence_threshold:
                medium_confidence += 1
            else:
                low_confidence += 1
        else:
            errors += 1

    return {
        "successful_matches": successful_matches,
        "high_confidence": high_confidence,
        "medium_confidence": medium_confidence,
        "low_confidence": low_confidence,
        "errors": errors,
    }
