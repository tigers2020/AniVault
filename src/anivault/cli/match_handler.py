"""Match command handler for AniVault CLI.

This module contains the business logic for the match command,
separated for better maintainability and single responsibility principle.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rich.console import Console

from anivault.core.matching.engine import MatchingEngine
from anivault.core.parser.anitopy_parser import AnitopyParser
from anivault.shared.constants.system import (
    CLI_INFO_COMMAND_COMPLETED,
    CLI_INFO_COMMAND_STARTED,
)

logger = logging.getLogger(__name__)


def handle_match_command(args: Any) -> int:
    """Handle the match command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger.info(CLI_INFO_COMMAND_STARTED.format(command="match"))

    try:
        import asyncio

        result = asyncio.run(_run_match_command_impl(args))

        if result == 0:
            logger.info(CLI_INFO_COMMAND_COMPLETED.format(command="match"))
        else:
            logger.error("Match command failed with exit code %s", result)

        return result

    except Exception:
        logger.exception("Error in match command")
        return 1


async def _run_match_command_impl(args: Any) -> int:
    """Run the match command with advanced matching engine.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        import asyncio

        from rich.console import Console
        from rich.progress import (
            BarColumn,
            Progress,
            SpinnerColumn,
            TaskProgressColumn,
            TextColumn,
        )

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
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return 1

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
            console.print(
                "[yellow]No anime files found in the specified directory[/yellow]",
            )
            return 0

        console.print(f"[blue]Found {len(anime_files)} anime files[/blue]")

        # Process files with progress bar and concurrent processing
        results = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Matching files...", total=len(anime_files))

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
                    progress.advance(task)
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

        # Display results
        _display_match_results_impl(results, console)
        return 0

    except Exception as e:
        console.print(f"[red]Error during matching: {e}[/red]")
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


def _display_match_results(results, console):
    """Display match results in a formatted table.

    Args:
        results: List of match results
        console: Rich console instance
    """
    from rich import box
    from rich.table import Table

    from anivault.shared.constants.matching import DEFAULT_CONFIDENCE_THRESHOLD

    # Create main results table
    table = Table(
        title="🎌 Anime File Matching Results",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
        title_style="bold cyan",
    )

    # Add columns with better styling
    table.add_column("📁 File", style="cyan", max_width=40, overflow="fold")
    table.add_column("🎬 Parsed Title", style="green", max_width=30, overflow="fold")
    table.add_column("📅 Year", style="yellow", justify="center", width=8)
    table.add_column("🎯 TMDB Match", style="magenta", max_width=35, overflow="fold")
    table.add_column("📊 Confidence", style="blue", justify="center", width=12)
    table.add_column("🏷️ Status", style="bold", justify="center", width=10)

    # Statistics counters
    total_files = len(results)
    successful_matches = 0
    high_confidence = 0
    medium_confidence = 0
    low_confidence = 0
    errors = 0

    for result in results:
        if "error" in result:
            # Handle error cases
            errors += 1
            table.add_row(
                result["file_path"],
                "❌ ERROR",
                "",
                "",
                "",
                "ERROR",
                style="red",
            )
            continue

        file_path = result["file_path"]
        parse_result = result.get("parse_result", {})
        match_result = result.get("match_result", {})
        normalized_query = result.get("normalized_query", {})

        # Extract parsed title
        parsed_title = parse_result.get("anime_title", "Unknown")
        if not parsed_title or parsed_title == "Unknown":
            parsed_title = normalized_query.get("title", "Unknown")

        # Extract year from parse result or normalized query
        year = parse_result.get("year", "")
        if not year:
            year = normalized_query.get("year", "")
        year_str = str(year) if year else "N/A"

        # Extract match information
        if match_result and "best_match" in match_result:
            successful_matches += 1
            best_match = match_result["best_match"]
            match_title = best_match.get("title", "No match")
            confidence = match_result.get("confidence_score", 0.0)

            # Format confidence with color coding
            if confidence >= DEFAULT_CONFIDENCE_THRESHOLD:
                confidence_str = f"[green]{confidence:.2f}[/green]"
                confidence_level = "HIGH"
                high_confidence += 1
            elif confidence >= 0.6:
                confidence_str = f"[yellow]{confidence:.2f}[/yellow]"
                confidence_level = "MED"
                medium_confidence += 1
            else:
                confidence_str = f"[red]{confidence:.2f}[/red]"
                confidence_level = "LOW"
                low_confidence += 1
        else:
            match_title = "No match"
            confidence_str = "N/A"
            confidence_level = "NONE"

        # Add row to table
        table.add_row(
            file_path,
            parsed_title,
            year_str,
            match_title,
            confidence_str,
            confidence_level,
        )

    # Display the table
    console.print(table)

    # Display summary statistics
    console.print("\n")
    summary_table = Table(
        title="📈 Matching Summary",
        box=box.SIMPLE,
        show_header=True,
        header_style="bold blue",
    )
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="green", justify="right")
    summary_table.add_column("Percentage", style="yellow", justify="right")

    summary_table.add_row("Total Files", str(total_files), "100%")
    summary_table.add_row(
        "Successful Matches",
        str(successful_matches),
        f"{(successful_matches/total_files*100):.1f}%",
    )
    summary_table.add_row(
        "High Confidence (≥0.8)",
        str(high_confidence),
        f"{(high_confidence/total_files*100):.1f}%",
    )
    summary_table.add_row(
        "Medium Confidence (0.6-0.8)",
        str(medium_confidence),
        f"{(medium_confidence/total_files*100):.1f}%",
    )
    summary_table.add_row(
        "Low Confidence (<0.6)",
        str(low_confidence),
        f"{(low_confidence/total_files*100):.1f}%",
    )
    summary_table.add_row("Errors", str(errors), f"{(errors/total_files*100):.1f}%")

    console.print(summary_table)

    # Display additional information if there are high-confidence matches
    if high_confidence > 0:
        console.print(
            f"\n[green]✅ {high_confidence} files matched with high confidence![/green]",
        )

    if errors > 0:
        console.print(f"\n[red]⚠️  {errors} files had processing errors[/red]")
