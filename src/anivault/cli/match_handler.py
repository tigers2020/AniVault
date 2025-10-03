"""Match command handler for AniVault CLI.

This module contains the business logic for the match command,
separated for better maintainability and single responsibility principle.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rich.console import Console

from anivault.cli.json_formatter import format_json_output
from anivault.cli.progress import create_progress_manager
from anivault.core.matching.engine import MatchingEngine
from anivault.core.parser.anitopy_parser import AnitopyParser
from anivault.shared.constants import CLI
from anivault.shared.errors import ApplicationError, InfrastructureError

logger = logging.getLogger(__name__)


def handle_match_command(args: Any) -> int:
    """Handle the match command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger.info(CLI.INFO_COMMAND_STARTED.format(command="match"))

    try:
        import asyncio

        result = asyncio.run(_run_match_command_impl(args))

        if result == 0:
            logger.info(CLI.INFO_COMMAND_COMPLETED.format(command="match"))
        else:
            logger.error("Match command failed with exit code %s", result)

        return result

    except ApplicationError as e:
        logger.exception(
            "Application error in match command",
            extra={"context": e.context, "error_code": e.code},
        )
        return 1
    except InfrastructureError as e:
        logger.exception(
            "Infrastructure error in match command",
            extra={"context": e.context, "error_code": e.code},
        )
        return 1
    except Exception:
        logger.exception("Unexpected error in match command")
        return 1


async def _run_match_command_impl(args: Any) -> int:  # noqa: PLR0911
    """Run the match command with advanced matching engine.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        import asyncio

        from rich.console import Console

        from anivault.core.matching.engine import MatchingEngine
        from anivault.core.parser.anitopy_parser import AnitopyParser
        from anivault.services import (
            JSONCacheV2,
            RateLimitStateMachine,
            SemaphoreManager,
            TMDBClient,
            TokenBucketRateLimiter,
        )

        console = Console()

        # Validate directory
        try:
            from anivault.cli.utils import validate_directory

            directory = validate_directory(args.directory)
        except ApplicationError as e:
            if hasattr(args, "json") and args.json:
                json_output = format_json_output(
                    success=False,
                    command="match",
                    errors=[f"Application error: {e.message}"],
                    data={"error_code": e.code, "context": e.context},
                )
                sys.stdout.buffer.write(json_output)
                sys.stdout.buffer.write(b"\n")
                sys.stdout.buffer.flush()
            else:
                console.print(f"[red]Application error: {e.message}[/red]")
            logger.exception(
                "Directory validation failed",
                extra={"context": e.context, "error_code": e.code},
            )
            return 1
        except InfrastructureError as e:
            if hasattr(args, "json") and args.json:
                json_output = format_json_output(
                    success=False,
                    command="match",
                    errors=[f"Infrastructure error: {e.message}"],
                    data={"error_code": e.code, "context": e.context},
                )
                sys.stdout.buffer.write(json_output)
                sys.stdout.buffer.write(b"\n")
                sys.stdout.buffer.flush()
            else:
                console.print(f"[red]Infrastructure error: {e.message}[/red]")
            logger.exception(
                "Directory validation failed",
                extra={"context": e.context, "error_code": e.code},
            )
            return 1
        except Exception as e:
            if hasattr(args, "json") and args.json:
                json_output = format_json_output(
                    success=False,
                    command="match",
                    errors=[f"Unexpected error: {e!s}"],
                    data={"error_type": type(e).__name__},
                )
                sys.stdout.buffer.write(json_output)
                sys.stdout.buffer.write(b"\n")
                sys.stdout.buffer.flush()
            else:
                console.print(f"[red]Unexpected error: {e}[/red]")
            logger.exception("Unexpected error during directory validation")
            return 1

        # Only show console output if not in JSON mode
        if not (hasattr(args, "json") and args.json):
            console.print(f"[green]Matching anime files in: {directory}[/green]")

        # Initialize services
        cache = JSONCacheV2(args.cache_dir)
        rate_limiter = TokenBucketRateLimiter(
            capacity=args.rate_limit,
            refill_rate=args.rate_limit,
        )
        semaphore_manager = SemaphoreManager(concurrency_limit=args.concurrent)
        state_machine = RateLimitStateMachine()

        tmdb_client = TMDBClient(
            rate_limiter=rate_limiter,
            semaphore_manager=semaphore_manager,
            state_machine=state_machine,
        )

        matching_engine = MatchingEngine(
            tmdb_client=tmdb_client,
            cache=cache,
        )

        # Initialize parser
        parser = AnitopyParser()

        # Find anime files
        anime_files = []
        for ext in args.extensions:
            anime_files.extend(directory.rglob(f"*{ext}"))

        if not anime_files:
            if hasattr(args, "json") and args.json:
                # Return empty results in JSON format
                match_data = _collect_match_data([], directory)
                json_output = format_json_output(
                    success=True,
                    command="match",
                    data=match_data,
                    warnings=["No anime files found in the specified directory"],
                )
                sys.stdout.buffer.write(json_output)
                sys.stdout.buffer.write(b"\n")
                sys.stdout.buffer.flush()
            else:
                console.print(
                    "[yellow]No anime files found in the specified directory[/yellow]",
                )
            return 0

        # Only show console output if not in JSON mode
        if not (hasattr(args, "json") and args.json):
            console.print(f"[blue]Found {len(anime_files)} anime files[/blue]")

        # Create progress manager (disabled for JSON output)
        progress_manager = create_progress_manager(
            disabled=(hasattr(args, "json") and args.json),
        )

        # Process files with progress bar and concurrent processing
        results = []
        with progress_manager.spinner("Matching files..."):
            # Create semaphore for concurrent processing
            semaphore = asyncio.Semaphore(args.workers)

            async def process_with_semaphore(file_path: Path) -> dict:
                """Process a file with semaphore control."""
                async with semaphore:
                    result = await _process_file_impl(
                        file_path=file_path,
                        parser=parser,
                        matching_engine=matching_engine,
                        console=console,
                    )
                    return result

            # Process all files concurrently
            results = await asyncio.gather(
                *[process_with_semaphore(file_path) for file_path in anime_files],
                return_exceptions=True,
            )

            # Handle any exceptions that occurred during processing
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    if not (hasattr(args, "json") and args.json):
                        console.print(
                            f"[red]Error processing {anime_files[i]}: {result}[/red]",
                        )
                    processed_results.append(
                        {
                            "file_path": str(anime_files[i]),
                            "error": str(result),
                        },
                    )
                else:
                    processed_results.append(result)

            results = processed_results

        # Check if JSON output is requested
        if hasattr(args, "json") and args.json:
            # Collect match data for JSON output
            match_data = _collect_match_data(results, directory)

            # Output JSON to stdout
            json_output = format_json_output(
                success=True,
                command="match",
                data=match_data,
            )
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            # Display results in human-readable format
            _display_match_results_impl(results, console)
        return 0

    except ApplicationError as e:
        if hasattr(args, "json") and args.json:
            json_output = format_json_output(
                success=False,
                command="match",
                errors=[f"Application error: {e.message}"],
                data={"error_code": e.code, "context": e.context},
            )
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            console.print(f"[red]Application error during matching: {e.message}[/red]")
        logger.exception(
            "Application error during matching",
            extra={"context": e.context, "error_code": e.code},
        )
        return 1
    except InfrastructureError as e:
        if hasattr(args, "json") and args.json:
            json_output = format_json_output(
                success=False,
                command="match",
                errors=[f"Infrastructure error: {e.message}"],
                data={"error_code": e.code, "context": e.context},
            )
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            console.print(
                f"[red]Infrastructure error during matching: {e.message}[/red]",
            )
        logger.exception(
            "Infrastructure error during matching",
            extra={"context": e.context, "error_code": e.code},
        )
        return 1
    except Exception as e:
        if hasattr(args, "json") and args.json:
            json_output = format_json_output(
                success=False,
                command="match",
                errors=[f"Unexpected error: {e!s}"],
                data={"error_type": type(e).__name__},
            )
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            console.print(f"[red]Unexpected error during matching: {e}[/red]")
        logger.exception("Unexpected error during matching")
        return 1


async def _process_file_impl(
    file_path: Path,
    parser: AnitopyParser,
    matching_engine: MatchingEngine,
    console: Console,
) -> dict:
    """Process a single anime file through the matching pipeline.

    Args:
        file_path: Path to the anime file
        parser: AnitopyParser instance
        matching_engine: MatchingEngine instance
        console: Rich console for output

    Returns:
        Dictionary containing processing results
    """
    try:
        # Parse the filename
        parsing_result = parser.parse(str(file_path))

        if not parsing_result:
            return {
                "file_path": str(file_path),
                "error": "Failed to parse filename",
            }

        # Match against TMDB
        match_result = await matching_engine.match(parsing_result)

        return {
            "file_path": str(file_path),
            "parsing_result": parsing_result,
            "match_result": match_result,
        }

    except Exception as e:
        return {
            "file_path": str(file_path),
            "error": str(e),
        }


def _display_match_results_impl(results: list, console: Console) -> None:
    """Display match results in a formatted table.

    Args:
        results: List of match results
        console: Rich console for output
    """
    from rich.table import Table

    if not results:
        console.print("[yellow]No results to display.[/yellow]")
        return

    # Create results table
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

        # Basic file info
        title = parsing_result.title or "Unknown"
        episode = str(parsing_result.episode) if parsing_result.episode else "-"
        quality = parsing_result.quality or "-"

        # TMDB match info
        if match_result and match_result.tmdb_data:
            tmdb_title = match_result.tmdb_data.get(
                "title",
            ) or match_result.tmdb_data.get("name", "Unknown")
            confidence = f"{match_result.match_confidence:.2f}"
        else:
            tmdb_title = "No match"
            confidence = "0.00"

        table.add_row(
            result["file_path"],
            title,
            episode,
            quality,
            tmdb_title,
            confidence,
        )

    console.print(table)


def _collect_match_data(results, directory):
    """Collect match data for JSON output.

    Args:
        results: List of match results
        directory: Scanned directory path

    Returns:
        Dictionary containing match statistics and file data
    """
    from pathlib import Path

    # Calculate basic statistics
    total_files = len(results)
    successful_matches = 0
    high_confidence_matches = 0
    medium_confidence_matches = 0
    low_confidence_matches = 0
    errors = 0
    total_size = 0
    file_counts_by_extension = {}
    scanned_paths = []

    # Process each result
    file_data = []
    for result in results:
        file_path = result.get("file_path", "Unknown")
        parsing_result = result.get("parsing_result")
        match_result = result.get("match_result")

        # Add to scanned paths
        scanned_paths.append(file_path)

        # Calculate file size
        try:
            file_size = Path(file_path).stat().st_size
            total_size += file_size
        except (OSError, TypeError):
            file_size = 0

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
            file_info["parsing_result"] = {
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

        # Add match result if available
        if match_result:
            successful_matches += 1
            confidence = getattr(match_result, "match_confidence", 0.0)

            # Categorize confidence levels
            if confidence >= 0.8:
                high_confidence_matches += 1
            elif confidence >= 0.6:
                medium_confidence_matches += 1
            else:
                low_confidence_matches += 1

            file_info["match_result"] = {
                "match_confidence": confidence,
                "tmdb_data": (
                    match_result.tmdb_data
                    if hasattr(match_result, "tmdb_data")
                    else None
                ),
                "enrichment_status": getattr(
                    match_result,
                    "enrichment_status",
                    "UNKNOWN",
                ),
            }
        elif "error" in result:
            errors += 1
            file_info["error"] = result["error"]
            file_info["match_result"] = {
                "match_confidence": 0.0,
                "tmdb_data": None,
                "enrichment_status": "ERROR",
            }
        else:
            file_info["match_result"] = {
                "match_confidence": 0.0,
                "tmdb_data": None,
                "enrichment_status": "NO_MATCH",
            }

        file_data.append(file_info)

    # Format total size in human-readable format
    def format_size(size_bytes):
        """Convert bytes to human-readable format."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    return {
        "match_summary": {
            "total_files": total_files,
            "successful_matches": successful_matches,
            "high_confidence_matches": high_confidence_matches,
            "medium_confidence_matches": medium_confidence_matches,
            "low_confidence_matches": low_confidence_matches,
            "errors": errors,
            "total_size_bytes": total_size,
            "total_size_formatted": format_size(total_size),
            "scanned_directory": str(directory),
            "success_rate": (
                (successful_matches / total_files * 100) if total_files > 0 else 0
            ),
        },
        "file_statistics": {
            "counts_by_extension": file_counts_by_extension,
            "scanned_paths": scanned_paths,
        },
        "files": file_data,
    }
