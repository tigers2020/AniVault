"""Scan command implementation."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import anitopy
import click
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from anivault.core.logging import get_logger
from anivault.scanner.file_scanner import scan_directory_with_stats

logger = get_logger(__name__)
console = Console()


@click.command()
@click.option(
    "--src",
    "-s",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Source directory to scan",
)
@click.option(
    "--extensions",
    "-e",
    multiple=True,
    help="File extensions to include (e.g., .mp4, .mkv)",
)
@click.option(
    "--max-workers",
    type=int,
    default=4,
    help="Maximum number of worker threads",
)
@click.option(
    "--recursive/--no-recursive",
    default=True,
    help="Scan subdirectories recursively",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file for scan results",
)
@click.option(
    "--stats-only",
    is_flag=True,
    help="Only show statistics, not file list",
)
@click.option(
    "--json",
    is_flag=True,
    help="Output in JSON format (NDJSON)",
)
@click.pass_context
def scan(
    ctx: click.Context,
    src: Path,
    extensions: tuple,
    max_workers: int,
    recursive: bool,
    output: Optional[Path],
    stats_only: bool,
    json: bool,
) -> None:
    """Scan directory for media files and extract metadata.

    This command scans the specified directory for media files, extracts
    metadata using anitopy, and provides statistics about the scan results.
    """
    json_output = json or ctx.obj.get("json_output", False)

    try:
        # Output scan start event
        if json_output:
            _output_json_event(
                "scan",
                "start",
                {
                    "source": str(src),
                    "extensions": list(extensions) if extensions else None,
                    "max_workers": max_workers,
                    "recursive": recursive,
                },
            )
        else:
            console.print(f"[blue]Scanning directory: {src}[/blue]")

        # Perform scan with progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
            disable=json_output,
        ) as progress:
            task = progress.add_task("Scanning files...", total=None)

            # Scan directory
            file_iterator, stats = scan_directory_with_stats(src)

            # Convert iterator to list and process files
            files = []
            for entry in file_iterator:
                file_info = {
                    "path": entry.path,
                    "name": entry.name,
                    "size": entry.stat().st_size if entry.is_file() else 0,
                    "is_file": entry.is_file(),
                    "is_dir": entry.is_dir(),
                }
                files.append(file_info)

            scan_results = {
                "files": files,
                "directories_scanned": stats.get("directories_scanned", 0),
                "errors": stats.get("permission_errors", 0)
                + stats.get("other_errors", 0),
            }

            progress.update(task, completed=True)

        # Process results with anitopy parsing
        files = scan_results.get("files", [])
        parsed_files = _parse_files_with_anitopy(files, json_output)

        total_files = len(files)
        total_dirs = scan_results.get("directories_scanned", 0)
        errors = scan_results.get("errors", 0)
        parsed_count = len([f for f in parsed_files if f.get("parsed")])
        parse_rate = parsed_count / total_files if total_files > 0 else 0.0

        # Output results
        if json_output:
            _output_json_event(
                "scan",
                "complete",
                {
                    "total_files": total_files,
                    "total_directories": total_dirs,
                    "errors": errors,
                    "parsed_files": parsed_count,
                    "parse_rate": parse_rate,
                    "files": parsed_files if not stats_only else None,
                },
            )
        else:
            console.print("[green]Scan completed successfully![/green]")
            console.print(f"Files found: {total_files}")
            console.print(f"Directories scanned: {total_dirs}")
            console.print(f"Files parsed: {parsed_count} ({parse_rate:.1%})")
            if errors > 0:
                console.print(f"[yellow]Errors encountered: {errors}[/yellow]")

        # Save to output file if specified
        if output:
            _save_scan_results(scan_results, output, stats_only)
            if not json_output:
                console.print(f"Results saved to: {output}")

        # Exit with appropriate code
        if errors > 0:
            sys.exit(10)  # Partial success
        else:
            sys.exit(0)  # Full success

    except Exception as e:
        logger.exception("Scan failed")
        if json_output:
            _output_json_error("E-SCAN-FAIL", str(e))
        else:
            console.print(f"[red]Scan failed: {e}[/red]")
        sys.exit(1)


def _output_json_event(phase: str, event: str, fields: Dict[str, Any]) -> None:
    """Output event in JSON format."""
    event_data = {
        "phase": phase,
        "event": event,
        "ts": datetime.utcnow().isoformat() + "Z",
        "fields": fields,
    }
    print(json.dumps(event_data))


def _output_json_error(error_code: str, message: str) -> None:
    """Output error in JSON format."""
    error_data = {
        "phase": "error",
        "event": "error",
        "ts": datetime.utcnow().isoformat() + "Z",
        "fields": {
            "error_code": error_code,
            "message": message,
            "level": "ERROR",
        },
    }
    print(json.dumps(error_data))


def _parse_files_with_anitopy(
    files: List[Dict[str, Any]],
    json_output: bool,
) -> List[Dict[str, Any]]:
    """Parse files using anitopy to extract metadata."""
    parsed_files = []

    for file_info in files:
        file_path = file_info.get("path", "")
        filename = Path(file_path).name

        try:
            # Parse filename with anitopy
            parsed_data = anitopy.parse(filename)

            # Create enhanced file info with parsed data
            enhanced_file = {
                **file_info,
                "parsed": True,
                "anime_title": parsed_data.get("anime_title", ""),
                "episode_number": parsed_data.get("episode_number", ""),
                "episode_title": parsed_data.get("episode_title", ""),
                "release_group": parsed_data.get("release_group", ""),
                "video_resolution": parsed_data.get("video_resolution", ""),
                "video_term": parsed_data.get("video_term", ""),
                "audio_term": parsed_data.get("audio_term", ""),
                "file_extension": parsed_data.get("file_extension", ""),
                "season": parsed_data.get("season", 1),
                "year": parsed_data.get("year", ""),
                "raw_parsed": parsed_data,
            }

            parsed_files.append(enhanced_file)

        except Exception as e:
            logger.debug("Failed to parse file %s: %s", filename, e)
            # Add file info without parsing
            enhanced_file = {
                **file_info,
                "parsed": False,
                "parse_error": str(e),
            }
            parsed_files.append(enhanced_file)

    return parsed_files


def _save_scan_results(
    results: Dict[str, Any],
    output_path: Path,
    stats_only: bool,
) -> None:
    """Save scan results to file."""
    output_data = {
        "scan_timestamp": datetime.utcnow().isoformat() + "Z",
        "total_files": len(results.get("files", [])),
        "total_directories": results.get("directories_scanned", 0),
        "errors": results.get("errors", 0),
    }

    if not stats_only:
        output_data["files"] = results.get("files", [])

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
