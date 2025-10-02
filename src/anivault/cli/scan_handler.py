"""Scan command handler for AniVault CLI.

This module contains the business logic for the scan command,
separated for better maintainability and single responsibility principle.
"""

import logging
from typing import Any

from anivault.shared.constants.system import (
    CLI_INFO_COMMAND_COMPLETED,
    CLI_INFO_COMMAND_STARTED,
)

logger = logging.getLogger(__name__)


def handle_scan_command(args: Any) -> int:
    """Handle the scan command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger.info(CLI_INFO_COMMAND_STARTED.format(command="scan"))

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
        from anivault.shared.constants.system import (
            CLI_ERROR_SCAN_FAILED,
            CLI_INDENT_SIZE,
            CLI_SUCCESS_RESULTS_SAVED,
            DEFAULT_ENCODING,
            DEFAULT_QUEUE_SIZE,
        )

        console = Console()

        # Validate directory
        try:
            from anivault.cli.utils import validate_directory

            directory = validate_directory(args.directory)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
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
                max_queue_size=DEFAULT_QUEUE_SIZE,
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

            with open(output_path, "w", encoding=DEFAULT_ENCODING) as f:
                json.dump(json_results, f, indent=CLI_INDENT_SIZE, ensure_ascii=False)

            console.print(
                f"[green]{CLI_SUCCESS_RESULTS_SAVED.format(path=output_path)}[/green]",
            )

        logger.info(CLI_INFO_COMMAND_COMPLETED.format(command="scan"))
        return 0

    except Exception as e:
        console.print(f"[red]{CLI_ERROR_SCAN_FAILED.format(error=e)}[/red]")
        logger.exception("Scan error")
        return 1


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
