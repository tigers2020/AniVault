"""Run command implementation - Full pipeline execution."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from anivault.core.logging import get_logger

logger = get_logger(__name__)
console = Console()


@click.command()
@click.option(
    "--src",
    "-s",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Source directory to process",
)
@click.option(
    "--dst",
    "-d",
    type=click.Path(path_type=Path),
    required=True,
    help="Destination directory for organized files",
)
@click.option(
    "--tmdb-key",
    envvar="TMDB_API_KEY",
    help="TMDB API key (can also be set via TMDB_API_KEY env var)",
)
@click.option(
    "--rate-limit",
    type=float,
    default=35.0,
    help="Rate limit in requests per second",
)
@click.option(
    "--concurrency",
    type=int,
    default=4,
    help="Maximum concurrent TMDB requests",
)
@click.option(
    "--language",
    default="en-US",
    help="Language for TMDB queries",
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
    help="Maximum number of worker threads for scanning",
)
@click.option(
    "--naming-schema",
    default="{title} ({year})/Season {season:02d}",
    help="Naming schema for organized files",
)
@click.option(
    "--conflict-resolution",
    type=click.Choice(["skip", "overwrite", "rename"]),
    default="rename",
    help="How to handle file conflicts",
)
@click.option(
    "--apply",
    is_flag=True,
    help="Apply changes (default is dry-run)",
)
@click.option(
    "--resume",
    is_flag=True,
    help="Resume from last checkpoint",
)
@click.option(
    "--checkpoint-dir",
    type=click.Path(path_type=Path),
    default=".anivault/checkpoints",
    help="Directory for checkpoint files",
)
@click.pass_context
def run(
    ctx: click.Context,
    src: Path,
    dst: Path,
    tmdb_key: Optional[str],
    rate_limit: float,
    concurrency: int,
    language: str,
    extensions: tuple,
    max_workers: int,
    naming_schema: str,
    conflict_resolution: str,
    apply: bool,
    resume: bool,
    checkpoint_dir: Path,
) -> None:
    """Run the complete AniVault pipeline.
    
    This command executes the full pipeline: scan -> match -> organize
    in a single operation with progress tracking and checkpoint support.
    """
    json_output = ctx.obj.get("json_output", False)
    
    try:
        # Validate TMDB key
        if not tmdb_key and not apply:  # Allow dry-run without API key
            error_msg = "TMDB API key is required for matching. Set TMDB_API_KEY environment variable or use --tmdb-key"
            if json_output:
                _output_json_error("E-TMDB-KEY", error_msg)
            else:
                console.print(f"[red]Error: {error_msg}[/red]")
            sys.exit(2)
        
        # Output run start event
        if json_output:
            _output_json_event("run", "start", {
                "source": str(src),
                "destination": str(dst),
                "rate_limit": rate_limit,
                "concurrency": concurrency,
                "language": language,
                "extensions": list(extensions) if extensions else None,
                "max_workers": max_workers,
                "naming_schema": naming_schema,
                "conflict_resolution": conflict_resolution,
                "apply": apply,
                "resume": resume
            })
        else:
            mode = "APPLY" if apply else "DRY-RUN"
            console.print(f"[blue]Running AniVault pipeline ({mode}): {src} -> {dst}[/blue]")
        
        # Create checkpoint directory
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Load checkpoint if resuming
        checkpoint = None
        if resume:
            checkpoint = _load_checkpoint(checkpoint_dir)
            if checkpoint:
                console.print(f"[yellow]Resuming from checkpoint: {checkpoint['timestamp']}[/yellow]")
        
        # Execute pipeline phases
        results = _execute_pipeline(
            src=src,
            dst=dst,
            tmdb_key=tmdb_key,
            rate_limit=rate_limit,
            concurrency=concurrency,
            language=language,
            extensions=list(extensions) if extensions else None,
            max_workers=max_workers,
            naming_schema=naming_schema,
            conflict_resolution=conflict_resolution,
            apply=apply,
            checkpoint=checkpoint,
            checkpoint_dir=checkpoint_dir,
            json_output=json_output
        )
        
        # Output final results
        if json_output:
            _output_json_event("run", "complete", results)
        else:
            console.print(f"[green]Pipeline completed successfully![/green]")
            console.print(f"Files scanned: {results['files_scanned']}")
            console.print(f"Files matched: {results['files_matched']}")
            console.print(f"Files organized: {results['files_organized']}")
            console.print(f"Errors: {results['errors']}")
        
        # Exit with appropriate code
        if results["errors"] > 0:
            sys.exit(10)  # Partial success
        else:
            sys.exit(0)  # Full success
            
    except Exception as e:
        logger.exception("Pipeline failed")
        if json_output:
            _output_json_error("E-RUN-FAIL", str(e))
        else:
            console.print(f"[red]Pipeline failed: {e}[/red]")
        sys.exit(1)


def _load_checkpoint(checkpoint_dir: Path) -> Optional[Dict[str, Any]]:
    """Load checkpoint from directory."""
    checkpoint_file = checkpoint_dir / "last_checkpoint.json"
    if checkpoint_file.exists():
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _save_checkpoint(checkpoint_dir: Path, phase: str, data: Dict[str, Any]) -> None:
    """Save checkpoint to directory."""
    checkpoint = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "phase": phase,
        "data": data
    }
    
    checkpoint_file = checkpoint_dir / "last_checkpoint.json"
    with open(checkpoint_file, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=2, ensure_ascii=False)


def _execute_pipeline(
    src: Path,
    dst: Path,
    tmdb_key: Optional[str],
    rate_limit: float,
    concurrency: int,
    language: str,
    extensions: Optional[list],
    max_workers: int,
    naming_schema: str,
    conflict_resolution: str,
    apply: bool,
    checkpoint: Optional[Dict[str, Any]],
    checkpoint_dir: Path,
    json_output: bool,
) -> Dict[str, Any]:
    """Execute the complete pipeline."""
    results = {
        "files_scanned": 0,
        "files_matched": 0,
        "files_organized": 0,
        "errors": 0
    }
    
    # Phase 1: Scan
    if not checkpoint or checkpoint.get("phase") != "scan":
        console.print("[blue]Phase 1: Scanning files...[/blue]")
        scan_results = _execute_scan_phase(src, extensions, max_workers, json_output)
        results["files_scanned"] = len(scan_results.get("files", []))
        _save_checkpoint(checkpoint_dir, "scan", scan_results)
    else:
        scan_results = checkpoint["data"]
        results["files_scanned"] = len(scan_results.get("files", []))
    
    # Phase 2: Match
    if not checkpoint or checkpoint.get("phase") != "match":
        console.print("[blue]Phase 2: Matching with TMDB...[/blue]")
        match_results = _execute_match_phase(
            scan_results, tmdb_key, rate_limit, concurrency, language, json_output
        )
        results["files_matched"] = len([m for m in match_results.get("results", []) if m.get("match")])
        _save_checkpoint(checkpoint_dir, "match", match_results)
    else:
        match_results = checkpoint["data"]
        results["files_matched"] = len([m for m in match_results.get("results", []) if m.get("match")])
    
    # Phase 3: Organize
    if not checkpoint or checkpoint.get("phase") != "organize":
        console.print("[blue]Phase 3: Organizing files...[/blue]")
        organize_results = _execute_organize_phase(
            match_results, src, dst, naming_schema, conflict_resolution, apply, json_output
        )
        results["files_organized"] = organize_results.get("files_moved", 0)
        results["errors"] = organize_results.get("errors", 0)
        _save_checkpoint(checkpoint_dir, "organize", organize_results)
    else:
        organize_results = checkpoint["data"]
        results["files_organized"] = organize_results.get("files_moved", 0)
        results["errors"] = organize_results.get("errors", 0)
    
    return results


def _execute_scan_phase(
    src: Path,
    extensions: Optional[list],
    max_workers: int,
    json_output: bool,
) -> Dict[str, Any]:
    """Execute scan phase."""
    # This would integrate with the scanner module
    # For now, return mock results
    return {
        "files": [],
        "directories_scanned": 0,
        "errors": 0
    }


def _execute_match_phase(
    scan_results: Dict[str, Any],
    tmdb_key: Optional[str],
    rate_limit: float,
    concurrency: int,
    language: str,
    json_output: bool,
) -> Dict[str, Any]:
    """Execute match phase."""
    # This would integrate with the matcher module
    # For now, return mock results
    return {
        "results": [],
        "total_files": 0,
        "matched_files": 0,
        "errors": 0
    }


def _execute_organize_phase(
    match_results: Dict[str, Any],
    src: Path,
    dst: Path,
    naming_schema: str,
    conflict_resolution: str,
    apply: bool,
    json_output: bool,
) -> Dict[str, Any]:
    """Execute organize phase."""
    # This would integrate with the organizer module
    # For now, return mock results
    return {
        "files_moved": 0,
        "files_skipped": 0,
        "errors": 0
    }


def _output_json_event(phase: str, event: str, fields: Dict[str, Any]) -> None:
    """Output event in JSON format."""
    event_data = {
        "phase": phase,
        "event": event,
        "ts": datetime.utcnow().isoformat() + "Z",
        "fields": fields
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
            "level": "ERROR"
        }
    }
    print(json.dumps(error_data))
