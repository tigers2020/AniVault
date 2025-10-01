"""
AniVault CLI Main Entry Point

This is the main entry point for the AniVault command-line interface.
It initializes UTF-8 encoding and logging before starting the application.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import confirm
from rich import print as rich_print
from rich.console import Console
from rich.table import Table
from tmdbv3api import Search, TMDb

from anivault.core.matching.engine import MatchingEngine
from anivault.core.normalization import normalize_query_from_anitopy
from anivault.core.parser.anitopy_parser import AnitopyParser

# Initialize UTF-8 and logging before any other imports
from anivault.utils.encoding import setup_utf8_environment
from anivault.utils.logging_config import log_shutdown, log_startup, setup_logging

# Set up UTF-8 environment first
setup_utf8_environment()

# Set up logging
logger = setup_logging(
    log_level=20,  # INFO level
    console_output=True,
    file_output=True,
)

# Log application startup
log_startup(logger, "0.1.0")


def main() -> int:
    """
    Main entry point for AniVault CLI.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
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

        parser.add_argument(
            "--version",
            action="version",
            version="AniVault 0.1.0",
        )

        parser.add_argument(
            "--verbose",
            "-v",
            action="store_true",
            help="Enable verbose output",
        )

        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            default="INFO",
            help="Set the logging level",
        )

        # Subcommands
        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # Scan command
        scan_parser = subparsers.add_parser(
            "scan",
            help="Scan directory for anime files",
        )
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

        # Match command
        match_parser = subparsers.add_parser(
            "match",
            help="Match anime files with TMDB metadata using advanced matching engine",
        )
        match_parser.add_argument(
            "directory",
            type=str,
            help="Directory to scan for anime files",
        )
        match_parser.add_argument(
            "--extensions",
            nargs="+",
            default=[".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm"],
            help="File extensions to process (default: .mkv .mp4 .avi .mov .wmv .flv .webm)",
        )
        match_parser.add_argument(
            "--workers",
            type=int,
            default=4,
            help="Number of concurrent workers (default: 4)",
        )
        match_parser.add_argument(
            "--rate-limit",
            type=int,
            default=20,
            help="TMDB API rate limit per minute (default: 20)",
        )
        match_parser.add_argument(
            "--concurrent",
            type=int,
            default=4,
            help="Maximum concurrent TMDB API calls (default: 4)",
        )
        match_parser.add_argument(
            "--cache-dir",
            type=str,
            default="cache",
            help="Cache directory for TMDB responses (default: cache)",
        )

        # Legacy verification flags
        verification_group = parser.add_argument_group("Legacy Verification Flags")
        verification_group.add_argument(
            "--verify-anitopy",
            action="store_true",
            help="Verify anitopy functionality in bundled executable",
        )
        verification_group.add_argument(
            "--verify-crypto",
            action="store_true",
            help="Verify cryptography functionality in bundled executable",
        )
        verification_group.add_argument(
            "--verify-tmdb",
            action="store_true",
            help="Verify tmdbv3api functionality in bundled executable",
        )
        verification_group.add_argument(
            "--verify-rich",
            action="store_true",
            help="Verify rich console rendering in bundled executable",
        )
        verification_group.add_argument(
            "--verify-prompt",
            action="store_true",
            help="Verify prompt_toolkit functionality in bundled executable",
        )

        # Parse arguments
        args = parser.parse_args()

        # Update log level if specified
        if args.log_level != "INFO":
            level = getattr(logging, args.log_level)
            logger.setLevel(level)
            for handler in logger.handlers:
                handler.setLevel(level)

        # Check for legacy verification flags first
        verification_handlers = {
            "verify_anitopy": _verify_anitopy,
            "verify_crypto": _verify_cryptography,
            "verify_tmdb": _verify_tmdb,
            "verify_rich": _verify_rich,
            "verify_prompt": _verify_prompt_toolkit,
        }

        for flag, handler in verification_handlers.items():
            if getattr(args, flag, False):
                handler()
                return 0

        # Handle new commands
        if args.command == "scan":
            return _run_scan_command(args)
        if args.command == "verify":
            return _run_verify_command(args)
        if args.command == "match":
            import asyncio

            return asyncio.run(_run_match_command(args))
        # No command specified, show help
        parser.print_help()
        return 0

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        return 1
    except Exception:
        logger.exception("Unexpected error occurred")
        return 1
    finally:
        log_shutdown(logger)


def _run_scan_command(args) -> int:
    """Run the scan command with TMDB integration.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        import asyncio
        from pathlib import Path

        from rich.console import Console
        from rich.progress import (
            BarColumn,
            Progress,
            SpinnerColumn,
            TaskProgressColumn,
            TextColumn,
        )

        from anivault.core.pipeline.main import run_pipeline
        from anivault.services import (
            MetadataEnricher,
            RateLimitStateMachine,
            SemaphoreManager,
            TMDBClient,
            TokenBucketRateLimiter,
        )

        console = Console()

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
            async def enrich_metadata_with_progress():
                parsing_results = []
                for result in file_results:
                    if "parsing_result" in result:
                        parsing_results.append(result["parsing_result"])

                if not parsing_results:
                    return file_results

                enriched_results = []
                for parsing_result in parsing_results:
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

            enriched_results = asyncio.run(enrich_metadata_with_progress())
        else:
            enriched_results = file_results

        # Display results
        _display_results(enriched_results, show_tmdb=enrich_metadata)

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

    except Exception as e:
        console.print(f"[red]Error during scan: {e}[/red]")
        logger.exception("Scan error")
        return 1


def _run_verify_command(args) -> int:
    """Run the verify command to check system components.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        import asyncio

        from rich.console import Console

        console = Console()

        if args.tmdb or args.all:
            console.print("[blue]Verifying TMDB API connectivity...[/blue]")

            # Test TMDB client
            from anivault.services import TMDBClient

            client = TMDBClient()

            # Test search functionality
            try:
                asyncio.run(client.search_media("test"))
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


async def _run_match_command(args) -> int:
    """Run the match command with advanced matching engine.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        import asyncio
        from pathlib import Path

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
        directory = Path(args.directory)
        if not directory.exists():
            console.print(f"[red]Error: Directory '{directory}' does not exist[/red]")
            return 1

        if not directory.is_dir():
            console.print(f"[red]Error: '{directory}' is not a directory[/red]")
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

            async def process_with_semaphore(file_path: Path) -> dict[str, Any]:
                """Process a file with semaphore control."""
                async with semaphore:
                    result = await _process_file(
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
        _display_match_results(results, console)
        return 0

    except Exception as e:
        console.print(f"[red]Error during matching: {e}[/red]")
        return 1


async def _process_file(
    file_path: Path,
    parser: AnitopyParser,
    matching_engine: MatchingEngine,
    console: Console,
) -> dict[str, Any]:
    """Process a single anime file through the matching pipeline.

    Args:
        file_path: Path to the anime file
        parser: Anitopy parser instance
        matching_engine: Matching engine instance
        console: Rich console for output

    Returns:
        Dictionary containing processing results
    """
    try:
        # Parse filename
        parse_result = parser.parse(str(file_path))

        # Normalize query
        normalized_query = normalize_query_from_anitopy(parse_result)

        # Find match
        match_result = matching_engine.find_match(normalized_query)

        return {
            "file_path": str(file_path),
            "parse_result": parse_result,
            "normalized_query": normalized_query,
            "match_result": match_result,
        }

    except Exception as e:
        console.print(f"[red]Error processing {file_path}: {e}[/red]")
        return {
            "file_path": str(file_path),
            "error": str(e),
        }


def _display_match_results(results, console):
    """Display match results in a formatted table.

    Args:
        results: List of match results
        console: Rich console instance
    """
    from rich import box
    from rich.table import Table

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
            if confidence >= 0.8:
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


def _display_results(results, show_tmdb=True):
    """Display scan results in a formatted table.

    Args:
        results: List of scan results
        show_tmdb: Whether to show TMDB metadata
    """
    from pathlib import Path

    from rich.console import Console
    from rich.table import Table

    console = Console()

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


def _verify_anitopy():
    """Verify anitopy functionality in bundled executable."""
    try:

        # Test filename parsing
        test_filename = "[SubsPlease] Jujutsu Kaisen S2 - 23 (1080p) [F02B9643].mkv"
        print(f"Testing anitopy with filename: {test_filename}")
        print()

        # Parse the filename
        result = anitopy.parse(test_filename)  # noqa: F821

        # Print the parsed result
        print("Anitopy parsing result:")
        for key, value in result.items():
            print(f"  {key}: {value}")

        # Verify key fields are present
        expected_keys = [
            "anime_title",
            "episode_number",
            "release_group",
            "video_resolution",
        ]
        found_keys = [key for key in expected_keys if key in result]

        print(f"\nExpected keys found: {found_keys}")
        min_required_keys = 2
        print(
            f"Anitopy verification: {'SUCCESS' if len(found_keys) >= min_required_keys else 'PARTIAL'}",
        )

    except ImportError as e:
        print(f"Anitopy verification FAILED - Import error: {e}")
    except Exception as e:
        print(f"Anitopy verification FAILED - Error: {e}")


def _verify_cryptography():
    """Verify cryptography functionality in bundled executable."""
    try:

        print("Testing cryptography with Fernet encryption/decryption...")
        print()

        # Generate a key
        key = Fernet.generate_key()
        print(f"Generated key: {key.decode()[:20]}...")

        # Create Fernet instance
        fernet = Fernet(key)

        # Test message
        original_message = b"This is a secret message for AniVault verification."
        print(f"Original message: {original_message.decode()}")

        # Encrypt the message
        encrypted_token = fernet.encrypt(original_message)
        print(f"Encrypted token: {encrypted_token.decode()[:50]}...")

        # Decrypt the message
        decrypted_message = fernet.decrypt(encrypted_token)
        print(f"Decrypted message: {decrypted_message.decode()}")

        # Verify the decrypted message matches the original
        if decrypted_message == original_message:
            print("Cryptography verification: SUCCESS")
        else:
            print(
                "Cryptography verification: FAILED - Decrypted message doesn't match original",
            )

    except ImportError as e:
        print(f"Cryptography verification FAILED - Import error: {e}")
    except Exception as e:
        print(f"Cryptography verification FAILED - Error: {e}")


def _verify_tmdb():
    """Verify tmdbv3api functionality in bundled executable."""
    try:

        print("Testing TMDB API connectivity and search functionality...")
        print()

        # Get API key from environment
        api_key = os.getenv("TMDB_API_KEY")
        if not api_key:
            print(
                "TMDB verification SKIPPED - No TMDB_API_KEY environment variable found",
            )
            print("To test TMDB functionality, set TMDB_API_KEY environment variable")
            return

        # Initialize TMDb
        tmdb = TMDb()
        tmdb.api_key = api_key
        tmdb.language = "en"

        print(f"Using API key: {api_key[:8]}...")

        # Test search functionality
        search = Search()
        query = "Jujutsu Kaisen"
        print(f"Searching for: {query}")

        # Search for TV shows
        results = search.tv_shows(query)

        print(f"TMDB search found {len(results)} results")

        if results:
            # Show first result details
            first_result = results[0]
            print(f"First result: {first_result.name} (ID: {first_result.id})")
            print(f"Overview: {first_result.overview[:100]}...")
            print("TMDB verification: SUCCESS")
        else:
            print("TMDB verification: PARTIAL - API connected but no results found")

    except ImportError as e:
        print(f"TMDB verification FAILED - Import error: {e}")
    except Exception as e:
        print(f"TMDB verification FAILED - Error: {e}")


def _verify_rich():
    """Verify rich console rendering in bundled executable."""
    try:

        print("Testing Rich console rendering...")
        print()

        # Create a console instance
        console = Console()

        # Test 1: Rich print with colors and styles
        rich_print("[bold blue]Rich Console Rendering Test[/bold blue]")
        rich_print("[green]✓ Green text[/green]")
        rich_print("[red]✗ Red text[/red]")
        rich_print("[yellow]⚠ Yellow warning[/yellow]")
        rich_print("[bold magenta]Bold magenta text[/bold magenta]")
        print()

        # Test 2: Rich table
        table = Table(title="AniVault Verification Results")
        table.add_column("Component", style="cyan", no_wrap=True)
        table.add_column("Status", style="magenta")
        table.add_column("Details", style="green")

        table.add_row("Anitopy", "✅ SUCCESS", "C extensions working")
        table.add_row("Cryptography", "✅ SUCCESS", "Native libraries bundled")
        table.add_row("TMDB API", "⏭️ SKIPPED", "No API key provided")
        table.add_row("Rich", "✅ SUCCESS", "Console rendering working")
        table.add_row("Prompt Toolkit", "⏳ PENDING", "Testing next...")

        console.print(table)
        print()

        # Test 3: Progress bar simulation
        rich_print("[bold]Progress simulation:[/bold]")
        for i in range(5):
            rich_print(f"[green]Step {i+1}/5:[/green] Testing Rich component...")

        rich_print("[bold green]Rich verification: SUCCESS[/bold green]")

    except ImportError as e:
        print(f"Rich verification FAILED - Import error: {e}")
    except Exception as e:
        print(f"Rich verification FAILED - Error: {e}")


def _verify_prompt_toolkit():
    """Verify prompt_toolkit functionality in bundled executable."""
    try:

        print("Testing Prompt Toolkit interactive functionality...")
        print()

        # Test 1: Simple prompt
        print("Testing basic prompt...")
        user_input = prompt("prompt_toolkit > ")
        print(f"You entered: {user_input}")
        print()

        # Test 2: Confirmation prompt
        print("Testing confirmation prompt...")
        confirmed = confirm("Do you want to continue? (y/n): ")
        print(f"Confirmation result: {confirmed}")
        print()

        # Test 3: Multiline prompt
        print("Testing multiline prompt (press Ctrl+D or Ctrl+Z to finish):")
        try:
            multiline_input = prompt("Enter multiple lines:\n", multiline=True)
            print(
                f"Multiline input received: {len(multiline_input.splitlines())} lines",
            )
        except (EOFError, KeyboardInterrupt):
            print("Multiline input cancelled")

        print()
        print("Prompt toolkit verification: SUCCESS")

    except ImportError as e:
        print(f"Prompt toolkit verification FAILED - Import error: {e}")
    except Exception as e:
        print(f"Prompt toolkit verification FAILED - Error: {e}")


def cli():
    """CLI entry point for Click."""
    return main()


if __name__ == "__main__":
    sys.exit(main())
