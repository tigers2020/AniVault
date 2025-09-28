"""Match command implementation."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

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
from anivault.services.cache_v2 import CacheV2
from anivault.services.matching_engine import MatchingConfig, MatchingEngine
from anivault.services.tmdb_client import RateLimitConfig, TMDBClient, TMDBConfig

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
            _output_json_event(
                "match",
                "start",
                {
                    "input": str(input),
                    "rate_limit": rate_limit,
                    "concurrency": concurrency,
                    "language": language,
                    "dry_run": dry_run,
                },
            )
        else:
            console.print(f"[blue]Starting TMDB matching for: {input}[/blue]")

        # Load scan results
        scan_results = _load_scan_results(input)
        files = scan_results.get("files", [])

        if not files:
            if json_output:
                _output_json_event(
                    "match",
                    "complete",
                    {
                        "total_files": 0,
                        "matched_files": 0,
                        "match_rate": 0.0,
                        "errors": 0,
                    },
                )
            else:
                console.print("[yellow]No files to match[/yellow]")
            return

        # Initialize TMDB client and matching engine
        tmdb_client = None
        matching_engine = None
        cache_v2 = None

        if not dry_run:
            tmdb_config = TMDBConfig(
                api_key=tmdb_key,
                rate_limit=RateLimitConfig(
                    max_requests_per_second=rate_limit,
                    max_concurrent_requests=concurrency,
                ),
            )
            tmdb_client = TMDBClient(tmdb_config)

            # Initialize enhanced matching engine
            matching_config = MatchingConfig(
                min_confidence=0.7,
                max_fallback_attempts=3,
                use_language_hints=True,
                use_year_hints=True,
                enable_query_variants=True,
                cache_results=True,
            )
            matching_engine = MatchingEngine(tmdb_client, matching_config)

            # Initialize cache v2
            cache_v2 = CacheV2(default_ttl=86400)  # 24 hours

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
            disable=json_output,
        ) as progress:
            task = progress.add_task("Matching files...", total=len(files))

            for file_info in files:
                try:
                    if dry_run:
                        # Simulate matching
                        match_result = _simulate_match(file_info)
                    else:
                        # Perform enhanced matching
                        match_result = _match_file_enhanced(
                            file_info,
                            matching_engine,
                            cache_v2,
                            language,
                        )

                    matched_files.append(match_result)

                except Exception as e:
                    logger.exception(
                        "Failed to match file: %s",
                        file_info.get("path", "unknown"),
                    )
                    errors += 1
                    matched_files.append(
                        {
                            "file": file_info,
                            "match": None,
                            "error": str(e),
                        },
                    )

                progress.advance(task)

        # Calculate enhanced statistics
        successful_matches = sum(1 for f in matched_files if f.get("match") is not None)
        high_confidence_matches = sum(
            1
            for result in matched_files
            if result.get("match") and result["match"].get("confidence", 0) >= 0.9
        )
        medium_confidence_matches = sum(
            1
            for result in matched_files
            if result.get("match") and 0.7 <= result["match"].get("confidence", 0) < 0.9
        )
        low_confidence_matches = sum(
            1
            for result in matched_files
            if result.get("match") and result["match"].get("confidence", 0) < 0.7
        )

        match_rate = successful_matches / len(files) if files else 0.0
        high_confidence_rate = high_confidence_matches / len(files) if files else 0.0

        # Get matching engine stats if available
        engine_stats = {}
        cache_stats = {}
        if matching_engine:
            engine_stats = matching_engine.get_stats()
        if cache_v2:
            cache_stats = cache_v2.get_stats()

        # Output results
        if json_output:
            _output_json_event(
                "match",
                "complete",
                {
                    "total_files": len(files),
                    "matched_files": successful_matches,
                    "match_rate": match_rate,
                    "high_confidence_matches": high_confidence_matches,
                    "high_confidence_rate": high_confidence_rate,
                    "medium_confidence_matches": medium_confidence_matches,
                    "low_confidence_matches": low_confidence_matches,
                    "errors": errors,
                    "engine_stats": engine_stats,
                    "cache_stats": cache_stats,
                    "results": matched_files if not dry_run else None,
                },
            )
        else:
            console.print("[green]Enhanced matching completed![/green]")
            console.print(f"Files processed: {len(files)}")
            console.print(f"Successfully matched: {successful_matches}")
            console.print(f"Match rate: {match_rate:.1%}")
            console.print(
                f"High confidence (≥90%): {high_confidence_matches} ({high_confidence_rate:.1%})",
            )
            console.print(f"Medium confidence (70-89%): {medium_confidence_matches}")
            console.print(f"Low confidence (<70%): {low_confidence_matches}")
            if errors > 0:
                console.print(f"[yellow]Errors: {errors}[/yellow]")

            # Show engine stats
            if engine_stats:
                console.print(
                    f"Cache hit rate: {engine_stats.get('cache_hit_rate', 0):.1%}",
                )
                console.print(
                    f"Average fallback attempts: {engine_stats.get('avg_fallback_attempts', 0):.1f}",
                )

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
        if cache_v2:
            cache_v2.save_cache()


def _load_scan_results(input_path: Path) -> Dict[str, Any]:
    """Load scan results from file or scan directory."""
    if input_path.is_file():
        with open(input_path, encoding="utf-8") as f:
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
                "is_dir": entry.is_dir(),
            }
            files.append(file_info)

        return {
            "files": files,
            "directories_scanned": stats.get("directories_scanned", 0),
            "errors": stats.get("permission_errors", 0) + stats.get("other_errors", 0),
        }


def _simulate_match(file_info: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate matching for dry run."""
    return {
        "file": file_info,
        "match": {
            "type": "simulated",
            "title": "Simulated Match",
            "confidence": 0.95,
        },
    }


def _match_file(
    file_info: Dict[str, Any],
    tmdb_client: TMDBClient,
    language: str,
) -> Dict[str, Any]:
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
            "error": "No TMDB results found",
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
            "confidence": 0.9,  # Placeholder confidence score
        },
    }


def _match_file_enhanced(
    file_info: Dict[str, Any],
    matching_engine: MatchingEngine,
    cache_v2: CacheV2,
    language: str,
) -> Dict[str, Any]:
    """Enhanced matching with accuracy optimization."""
    # Extract title and year from file info
    title = file_info.get("title", "")
    year = file_info.get("year")

    if not title:
        raise ValueError("No title found in file info")

    # Check cache first
    cache_key = f"match:{title}:{year}:{language}"
    cached_result = cache_v2.get(cache_key)
    if cached_result:
        logger.debug(f"Cache hit for: {title}")
        return cached_result

    try:
        # Use enhanced matching engine
        match_result = matching_engine.match_anime(title, year, language)

        # Convert to legacy format
        if match_result.tmdb_id:
            result = {
                "file": file_info,
                "match": {
                    "tmdb_id": match_result.tmdb_id,
                    "title": match_result.title,
                    "original_title": match_result.original_title,
                    "overview": match_result.overview,
                    "first_air_date": match_result.first_air_date,
                    "popularity": match_result.popularity,
                    "vote_average": match_result.vote_average,
                    "vote_count": match_result.vote_count,
                    "confidence": match_result.confidence,
                    "match_type": match_result.match_type,
                    "query_used": match_result.query_used,
                    "fallback_attempts": match_result.fallback_attempts,
                },
            }
        else:
            result = {
                "file": file_info,
                "match": None,
                "error": f"No match found (confidence: {match_result.confidence:.2f})",
            }

        # Cache the result
        cache_v2.set(cache_key, result, ttl=86400, tags=["tmdb_match"])

        return result

    except Exception as e:
        logger.error(f"Enhanced matching failed for {title}: {e}")
        return {
            "file": file_info,
            "match": None,
            "error": f"Enhanced matching failed: {e!s}",
        }


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


def _save_match_results(
    results: List[Dict[str, Any]],
    output_path: Path,
    dry_run: bool,
) -> None:
    """Save match results to file."""
    output_data = {
        "match_timestamp": datetime.utcnow().isoformat() + "Z",
        "dry_run": dry_run,
        "total_files": len(results),
        "successful_matches": sum(1 for r in results if r.get("match") is not None),
        "results": results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
