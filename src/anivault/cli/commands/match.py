"""Match command implementation."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from anivault.core.logging import get_logger
from anivault.services.tmdb_client import TMDBClient, TMDBConfig, RateLimitConfig

logger = get_logger(__name__)
console = Console()


@click.command()
@click.option(
    "--input",
    "-i",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Input file with scan results or directory to scan",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file for match results",
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
    "--dry-run",
    is_flag=True,
    help="Perform matching without making actual API calls",
)
@click.option(
    "--json",
    is_flag=True,
    help="Output in JSON format (NDJSON)",
)
@click.pass_context
def match(
    ctx: click.Context,
    input: Path,
    output: Optional[Path],
    tmdb_key: Optional[str],
    rate_limit: float,
    concurrency: int,
    language: str,
    dry_run: bool,
    json: bool,
) -> None:
    """Match files with TMDB metadata.
    
    This command takes scan results and attempts to match files with
    TMDB metadata using intelligent query normalization and fallback strategies.
    """
    json_output = json or ctx.obj.get("json_output", False)
    
    try:
        # Validate TMDB key
        if not tmdb_key and not dry_run:
            error_msg = "TMDB API key is required. Set TMDB_API_KEY environment variable or use --tmdb-key"
            if json_output:
                _output_json_error("E-TMDB-KEY", error_msg)
            else:
                console.print(f"[red]Error: {error_msg}[/red]")
            sys.exit(2)
        
        # Output match start event
        if json_output:
            _output_json_event("match", "start", {
                "input": str(input),
                "rate_limit": rate_limit,
                "concurrency": concurrency,
                "language": language,
                "dry_run": dry_run
            })
        else:
            console.print(f"[blue]Starting TMDB matching for: {input}[/blue]")
        
        # Load scan results
        scan_results = _load_scan_results(input)
        files = scan_results.get("files", [])
        
        if not files:
            if json_output:
                _output_json_event("match", "complete", {
                    "total_files": 0,
                    "matched_files": 0,
                    "match_rate": 0.0,
                    "errors": 0
                })
            else:
                console.print("[yellow]No files to match[/yellow]")
            return
        
        # Initialize TMDB client
        tmdb_client = None
        if not dry_run:
            tmdb_config = TMDBConfig(
                api_key=tmdb_key,
                rate_limit=RateLimitConfig(
                    max_requests_per_second=rate_limit,
                    max_concurrent_requests=concurrency
                )
            )
            tmdb_client = TMDBClient(tmdb_config)
        
        # Perform matching with progress tracking
        matched_files = []
        errors = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
            disable=json_output
        ) as progress:
            task = progress.add_task("Matching files...", total=len(files))
            
            for file_info in files:
                try:
                    if dry_run:
                        # Simulate matching
                        match_result = _simulate_match(file_info)
                    else:
                        # Perform actual matching
                        match_result = _match_file(file_info, tmdb_client, language)
                    
                    matched_files.append(match_result)
                    
                except Exception as e:
                    logger.exception("Failed to match file: %s", file_info.get("path", "unknown"))
                    errors += 1
                    matched_files.append({
                        "file": file_info,
                        "match": None,
                        "error": str(e)
                    })
                
                progress.advance(task)
        
        # Calculate statistics
        successful_matches = sum(1 for f in matched_files if f.get("match") is not None)
        match_rate = successful_matches / len(files) if files else 0.0
        
        # Output results
        if json_output:
            _output_json_event("match", "complete", {
                "total_files": len(files),
                "matched_files": successful_matches,
                "match_rate": match_rate,
                "errors": errors,
                "results": matched_files if not dry_run else None
            })
        else:
            console.print(f"[green]Matching completed![/green]")
            console.print(f"Files processed: {len(files)}")
            console.print(f"Successfully matched: {successful_matches}")
            console.print(f"Match rate: {match_rate:.1%}")
            if errors > 0:
                console.print(f"[yellow]Errors: {errors}[/yellow]")
        
        # Save results if output specified
        if output:
            _save_match_results(matched_files, output, dry_run)
            if not json_output:
                console.print(f"Results saved to: {output}")
        
        # Exit with appropriate code
        if errors > 0:
            sys.exit(10)  # Partial success
        else:
            sys.exit(0)  # Full success
            
    except Exception as e:
        logger.exception("Match failed")
        if json_output:
            _output_json_error("E-MATCH-FAIL", str(e))
        else:
            console.print(f"[red]Match failed: {e}[/red]")
        sys.exit(1)
    finally:
        if tmdb_client:
            tmdb_client.close()


def _load_scan_results(input_path: Path) -> Dict[str, Any]:
    """Load scan results from file or scan directory."""
    if input_path.is_file():
        with open(input_path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        # If it's a directory, scan it first
        from anivault.scanner.file_scanner import scan_directory_with_stats
        
        file_iterator, stats = scan_directory_with_stats(input_path)
        
        # Convert iterator to list
        files = []
        for entry in file_iterator:
            file_info = {
                "path": entry.path,
                "name": entry.name,
                "size": entry.stat().st_size if entry.is_file() else 0,
                "is_file": entry.is_file(),
                "is_dir": entry.is_dir()
            }
            files.append(file_info)
        
        return {
            "files": files,
            "directories_scanned": stats.get("directories_scanned", 0),
            "errors": stats.get("permission_errors", 0) + stats.get("other_errors", 0)
        }


def _simulate_match(file_info: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate matching for dry run."""
    return {
        "file": file_info,
        "match": {
            "type": "simulated",
            "title": "Simulated Match",
            "confidence": 0.95
        }
    }


def _match_file(file_info: Dict[str, Any], tmdb_client: TMDBClient, language: str) -> Dict[str, Any]:
    """Match a single file with TMDB."""
    # Extract title from file info
    title = file_info.get("title", "")
    if not title:
        raise ValueError("No title found in file info")
    
    # Search TMDB
    search_results = tmdb_client.search_tv(title)
    
    if not search_results:
        return {
            "file": file_info,
            "match": None,
            "error": "No TMDB results found"
        }
    
    # Take the first result as the best match
    best_match = search_results[0]
    
    return {
        "file": file_info,
        "match": {
            "tmdb_id": best_match.get("id"),
            "title": best_match.get("name"),
            "overview": best_match.get("overview"),
            "first_air_date": best_match.get("first_air_date"),
            "confidence": 0.9  # Placeholder confidence score
        }
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


def _save_match_results(results: List[Dict[str, Any]], output_path: Path, dry_run: bool) -> None:
    """Save match results to file."""
    output_data = {
        "match_timestamp": datetime.utcnow().isoformat() + "Z",
        "dry_run": dry_run,
        "total_files": len(results),
        "successful_matches": sum(1 for r in results if r.get("match") is not None),
        "results": results
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
