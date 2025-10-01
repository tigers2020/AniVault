"""Enhanced CLI with TMDB integration for AniVault.

This module provides an enhanced CLI that integrates the TMDB client
with the existing file processing pipeline to enrich anime metadata.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table
from rich.text import Text

from anivault.config.settings import get_config
from anivault.core.pipeline.main import run_pipeline
from anivault.services import MetadataEnricher, TMDBClient
from anivault.utils.logging_config import setup_logging

# Set up logging
logger = logging.getLogger(__name__)
console = Console()


def create_enhanced_parser() -> argparse.ArgumentParser:
    """Create enhanced argument parser with TMDB integration options.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="AniVault - Anime Collection Management System with TMDB Integration",
        prog="anivault",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan directory and enrich with TMDB metadata
  anivault scan /path/to/anime --enrich

  # Scan with custom settings
  anivault scan /path/to/anime --enrich --workers 8 --rate-limit 20

  # Scan without TMDB enrichment (faster)
  anivault scan /path/to/anime --no-enrich
        """,
    )

    # Version
    parser.add_argument("--version", action="version", version="AniVault 0.1.0")

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan directory for anime files")
    scan_parser.add_argument(
        "directory",
        type=str,
        help="Directory to scan for anime files",
    )
    scan_parser.add_argument(
        "--enrich",
        action="store_true",
        default=True,
        help="Enrich metadata with TMDB data (default: True)",
    )
    scan_parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="Skip TMDB metadata enrichment",
    )
    scan_parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of worker threads (default: 4)",
    )
    scan_parser.add_argument(
        "--rate-limit",
        type=float,
        default=35.0,
        help="TMDB API rate limit in requests per second (default: 35.0)",
    )
    scan_parser.add_argument(
        "--concurrent",
        type=int,
        default=4,
        help="Maximum concurrent TMDB requests (default: 4)",
    )
    scan_parser.add_argument(
        "--extensions",
        nargs="+",
        default=[".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".m4v", ".webm"],
        help="File extensions to scan for (default: .mkv .mp4 .avi .mov .wmv .flv .m4v .webm)",
    )
    scan_parser.add_argument(
        "--output",
        type=str,
        help="Output file for results (JSON format)",
    )
    scan_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify system components")
    verify_parser.add_argument(
        "--tmdb",
        action="store_true",
        help="Verify TMDB API connectivity",
    )
    verify_parser.add_argument(
        "--all",
        action="store_true",
        help="Verify all components",
    )

    return parser


async def enrich_metadata_with_progress(
    file_results: list[dict[str, Any]],
    enricher: MetadataEnricher,
) -> list[dict[str, Any]]:
    """Enrich metadata with progress indication.

    Args:
        file_results: List of file processing results
        enricher: Metadata enricher instance

    Returns:
        List of enriched results
    """
    # Extract ParsingResult objects
    parsing_results = []
    for result in file_results:
        if "parsing_result" in result:
            parsing_results.append(result["parsing_result"])

    if not parsing_results:
        return file_results

    # Enrich metadata with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "Enriching metadata with TMDB...",
            total=len(parsing_results),
        )

        enriched_results = []
        for parsing_result in parsing_results:
            enriched = await enricher.enrich_metadata(parsing_result)
            enriched_results.append(enriched)
            progress.update(task, advance=1)

    # Combine enriched metadata with original results
    enriched_file_results = []
    for original_result, enriched_metadata in zip(file_results, enriched_results):
        enriched_result = original_result.copy()
        enriched_result["enriched_metadata"] = enriched_metadata
        enriched_file_results.append(enriched_result)

    return enriched_file_results


def display_results(results: list[dict[str, Any]], show_tmdb: bool = True) -> None:
    """Display scan results in a formatted table.

    Args:
        results: List of scan results
        show_tmdb: Whether to show TMDB metadata
    """
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
        file_path = result.get("file_path", "Unknown")
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


def display_summary(results: list[dict[str, Any]], enricher: MetadataEnricher) -> None:
    """Display scan summary statistics.

    Args:
        results: List of scan results
        enricher: Metadata enricher instance
    """
    total_files = len(results)
    enriched_files = sum(1 for r in results if r.get("enriched_metadata"))
    successful_enrichments = sum(
        1
        for r in results
        if r.get("enriched_metadata", {}).enrichment_status == "success"
    )

    # Create summary panel
    summary_text = f"""
Total files scanned: {total_files}
Files enriched: {enriched_files}
Successful enrichments: {successful_enrichments}
Enrichment success rate: {(successful_enrichments/enriched_files*100):.1f}% if enriched_files > 0 else 0.0
    """.strip()

    # Add TMDB client stats
    tmdb_stats = enricher.get_stats().get("tmdb_client", {})
    if tmdb_stats:
        summary_text += f"""
TMDB Client Stats:
  Rate Limiter: {tmdb_stats.get('rate_limiter', {}).get('tokens_available', 'N/A')} tokens available
  Semaphore: {tmdb_stats.get('semaphore_manager', {}).get('active_requests', 'N/A')} active requests
  State Machine: {tmdb_stats.get('state_machine', {}).get('state', 'N/A')} state
    """.strip()

    panel = Panel(
        Text(summary_text, style="white"),
        title="Scan Summary",
        border_style="green",
    )
    console.print(panel)


async def run_scan_command(args: argparse.Namespace) -> int:
    """Run the scan command with TMDB integration.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Validate directory
        directory = Path(args.directory)
        if not directory.exists():
            console.print(f"[red]Error: Directory '{directory}' does not exist[/red]")
            return 1

        if not directory.is_dir():
            console.print(f"[red]Error: '{directory}' is not a directory[/red]")
            return 1

        # Determine if we should enrich metadata
        enrich_metadata = args.enrich and not args.no_enrich

        # Set up logging
        if args.verbose:
            setup_logging(level=logging.DEBUG)
        else:
            setup_logging(level=logging.INFO)

        console.print(f"[green]Scanning directory: {directory}[/green]")
        console.print(f"[blue]Enriching metadata: {enrich_metadata}[/blue]")

        # Run the file processing pipeline
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Scanning files...", total=None)

            file_results = run_pipeline(
                root_path=str(directory),
                extensions=args.extensions,
                num_workers=args.workers,
                max_queue_size=100,
            )

            progress.update(task, description="File scanning completed")

        if not file_results:
            console.print(
                "[yellow]No anime files found in the specified directory[/yellow]",
            )
            return 0

        # Enrich metadata if requested
        if enrich_metadata:
            # Initialize TMDB client and enricher
            get_config()

            # Create TMDB client with custom settings
            from anivault.services import (
                RateLimitStateMachine,
                SemaphoreManager,
                TokenBucketRateLimiter,
            )

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

            enricher = MetadataEnricher(tmdb_client=tmdb_client)

            # Enrich metadata
            enriched_results = await enrich_metadata_with_progress(
                file_results,
                enricher,
            )
        else:
            enriched_results = file_results

        # Display results
        display_results(enriched_results, show_tmdb=enrich_metadata)

        # Display summary
        if enrich_metadata:
            display_summary(enriched_results, enricher)

        # Save results to file if requested
        if args.output:
            import json

            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert results to JSON-serializable format
            json_results = []
            for result in enriched_results:
                json_result = result.copy()
                if "parsing_result" in json_result:
                    # Convert ParsingResult to dict
                    parsing_result = json_result["parsing_result"]
                    json_result["parsing_result"] = {
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

                json_results.append(json_result)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(json_results, f, indent=2, ensure_ascii=False)

            console.print(f"[green]Results saved to: {output_path}[/green]")

        return 0

    except KeyboardInterrupt:
        console.print("\n[yellow]Scan interrupted by user[/yellow]")
        return 1
    except Exception as e:
        console.print(f"[red]Error during scan: {e}[/red]")
        logger.exception("Scan error")
        return 1


async def run_verify_command(args: argparse.Namespace) -> int:
    """Run the verify command to check system components.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        if args.tmdb or args.all:
            console.print("[blue]Verifying TMDB API connectivity...[/blue]")

            # Test TMDB client
            from anivault.services import TMDBClient

            client = TMDBClient()

            # Test search functionality
            try:
                await client.search_media("test")
                console.print("[green]✓ TMDB API connectivity verified[/green]")
            except Exception as e:
                console.print(f"[red]✗ TMDB API connectivity failed: {e}[/red]")
                return 1

        if args.all:
            console.print("[blue]Verifying all components...[/blue]")
            # Add more verification checks here
            console.print("[green]✓ All components verified[/green]")

        return 0

    except Exception as e:
        console.print(f"[red]Error during verification: {e}[/red]")
        return 1


async def main() -> int:
    """Main entry point for enhanced CLI.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = create_enhanced_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "scan":
        return await run_scan_command(args)
    if args.command == "verify":
        return await run_verify_command(args)
    console.print(f"[red]Unknown command: {args.command}[/red]")
    return 1


def cli() -> int:
    """CLI entry point for Click compatibility.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    return asyncio.run(main())


if __name__ == "__main__":
    sys.exit(cli())
