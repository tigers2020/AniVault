"""Match command handler for AniVault CLI.

This module contains the business logic for the match command,
separated for better maintainability and single responsibility principle.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from rich.console import Console

from anivault.cli.common.context import get_cli_context
from anivault.cli.common.models import MatchOptions
from anivault.cli.json_formatter import format_json_output
from anivault.cli.progress import create_progress_manager
from anivault.core.matching.engine import MatchingEngine
from anivault.core.parser.anitopy_parser import AnitopyParser
from anivault.shared.constants import CLI, FileSystem
from anivault.shared.constants.cli import CLIFormatting, CLIMessages
from anivault.shared.errors import ApplicationError, InfrastructureError

logger = logging.getLogger(__name__)


def handle_match_command(options: MatchOptions) -> int:
    """Handle the match command.

    Args:
        options: Validated match command options

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger.info(CLI.INFO_COMMAND_STARTED.format(command=CLIMessages.CommandNames.MATCH))

    try:
        import asyncio

        result = asyncio.run(_run_match_command_impl(options))

        if result == 0:
            logger.info(
                CLI.INFO_COMMAND_COMPLETED.format(
                    command=CLIMessages.CommandNames.MATCH,
                ),
            )
        else:
            logger.error("Match command failed with exit code %s", result)

        return result

    except ApplicationError as e:
        logger.exception(
            "%sin match command",
            CLIMessages.Error.APPLICATION_ERROR,
            extra={
                CLIMessages.StatusKeys.CONTEXT: e.context,
                CLIMessages.StatusKeys.ERROR_CODE: e.code,
            },
        )
        return 1
    except InfrastructureError as e:
        logger.exception(
            "%sin match command",
            CLIMessages.Error.INFRASTRUCTURE_ERROR,
            extra={
                CLIMessages.StatusKeys.CONTEXT: e.context,
                CLIMessages.StatusKeys.ERROR_CODE: e.code,
            },
        )
        return 1
    except Exception:
        logger.exception("%sin match command", CLIMessages.Error.UNEXPECTED_ERROR)
        return 1


async def _run_match_command_impl(options: MatchOptions) -> int:  # noqa: PLR0911
    """Run the match command with advanced matching engine.

    Args:
        options: Validated match command options

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
            from anivault.cli.common.context import validate_directory

            directory = validate_directory(str(options.directory))
        except ApplicationError as e:
            if options.json_output is not None:
                json_output = format_json_output(
                    success=False,
                    command=CLIMessages.CommandNames.MATCH,
                    errors=[f"Application error: {e.message}"],
                    data={"error_code": e.code, "context": e.context},
                )
                sys.stdout.buffer.write(json_output)
                sys.stdout.buffer.write(b"\n")
                sys.stdout.buffer.flush()
            else:
                console.print(
                    CLIFormatting.format_colored_message(
                        f"Application error: {e.message}",
                        "error",
                    ),
                )
            logger.exception(
                CLIMessages.Error.DIRECTORY_VALIDATION_FAILED,
                extra={
                    CLIMessages.StatusKeys.CONTEXT: e.context,
                    CLIMessages.StatusKeys.ERROR_CODE: e.code,
                },
            )
            return 1
        except InfrastructureError as e:
            if options.json_output is not None:
                json_output = format_json_output(
                    success=False,
                    command=CLIMessages.CommandNames.MATCH,
                    errors=[f"Infrastructure error: {e.message}"],
                    data={"error_code": e.code, "context": e.context},
                )
                sys.stdout.buffer.write(json_output)
                sys.stdout.buffer.write(b"\n")
                sys.stdout.buffer.flush()
            else:
                console.print(
                    CLIFormatting.format_colored_message(
                        f"Infrastructure error: {e.message}",
                        "error",
                    ),
                )
            logger.exception(
                CLIMessages.Error.DIRECTORY_VALIDATION_FAILED,
                extra={
                    CLIMessages.StatusKeys.CONTEXT: e.context,
                    CLIMessages.StatusKeys.ERROR_CODE: e.code,
                },
            )
            return 1
        except Exception as e:
            if options.json_output is not None:
                json_output = format_json_output(
                    success=False,
                    command=CLIMessages.CommandNames.MATCH,
                    errors=[f"Unexpected error: {e!s}"],
                    data={"error_type": type(e).__name__},
                )
                sys.stdout.buffer.write(json_output)
                sys.stdout.buffer.write(b"\n")
                sys.stdout.buffer.flush()
            else:
                console.print(
                    CLIFormatting.format_colored_message(
                        f"Unexpected error: {e}",
                        "error",
                    ),
                )
            logger.exception(CLIMessages.Error.UNEXPECTED_ERROR_DURING_VALIDATION)
            return 1

        # Only show console output if not in JSON mode
        if not options.json_output:
            console.print(
                CLIFormatting.format_colored_message(
                    f"Matching anime files in: {directory}",
                    "success",
                ),
            )

        # Initialize services
        cache = JSONCacheV2(FileSystem.CACHE_DIRECTORY)  # Default cache directory
        rate_limiter = TokenBucketRateLimiter(
            capacity=50,  # Default rate limit
            refill_rate=50,
        )
        semaphore_manager = SemaphoreManager(concurrency_limit=4)  # Default concurrency
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
        anime_files: list[Path] = []
        for ext in FileSystem.CLI_VIDEO_EXTENSIONS:
            anime_files.extend(directory.rglob(f"*{ext}"))

        if not anime_files:
            if options.json_output is not None:
                # Return empty results in JSON format
                match_data = _collect_match_data([], directory)
                json_output = format_json_output(
                    success=True,
                    command=CLIMessages.CommandNames.MATCH,
                    data=match_data,
                    warnings=[CLIMessages.Info.NO_ANIME_FILES_FOUND],
                )
                sys.stdout.buffer.write(json_output)
                sys.stdout.buffer.write(b"\n")
                sys.stdout.buffer.flush()
            else:
                console.print(
                    CLIFormatting.format_colored_message(
                        CLIMessages.Info.NO_ANIME_FILES_FOUND,
                        "warning",
                    ),
                )
            return 0

        # Only show console output if not in JSON mode
        if not options.json_output:
            console.print(
                CLIFormatting.format_colored_message(
                    f"Found {len(anime_files)} anime files",
                    "info",
                ),
            )

        # Create progress manager (disabled for JSON output)
        progress_manager = create_progress_manager(
            disabled=options.json_output,
        )

        # Process files with progress bar and concurrent processing
        results = []
        with progress_manager.spinner(CLIMessages.Info.SCANNING_FILES):
            # Create semaphore for concurrent processing
            semaphore = asyncio.Semaphore(4)  # Default workers

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
                    if not options.json_output:
                        console.print(
                            CLIFormatting.format_colored_message(
                                f"Error processing {anime_files[i]}: {result}",
                                "error",
                            ),
                        )
                    processed_results.append(
                        {
                            CLIMessages.StatusKeys.FILE_PATH: str(anime_files[i]),
                            "error": str(result),
                        },
                    )
                elif isinstance(result, dict):
                    processed_results.append(result)
                else:
                    # Handle unexpected result type
                    processed_results.append(
                        {
                            CLIMessages.StatusKeys.FILE_PATH: str(anime_files[i]),
                            "error": "Unexpected result type",
                        },
                    )

            processed_results_final: list[dict[str, str]] = processed_results

        # Check if JSON output is requested
        if options.json_output is not None:
            # Collect match data for JSON output
            match_data = _collect_match_data(processed_results_final, directory)

            # Output JSON to stdout
            json_output = format_json_output(
                success=True,
                command=CLIMessages.CommandNames.MATCH,
                data=match_data,
            )
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            # Display results in human-readable format
            _display_match_results_impl(processed_results_final, console)
        return 0

    except ApplicationError as e:
        if options.json_output is not None:
            json_output = format_json_output(
                success=False,
                command=CLIMessages.CommandNames.MATCH,
                errors=[f"{CLIMessages.Error.APPLICATION_ERROR}{e.message}"],
                data={
                    CLIMessages.StatusKeys.ERROR_CODE: e.code,
                    CLIMessages.StatusKeys.CONTEXT: e.context,
                },
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
        if options.json_output is not None:
            json_output = format_json_output(
                success=False,
                command=CLIMessages.CommandNames.MATCH,
                errors=[f"{CLIMessages.Error.INFRASTRUCTURE_ERROR}{e.message}"],
                data={
                    CLIMessages.StatusKeys.ERROR_CODE: e.code,
                    CLIMessages.StatusKeys.CONTEXT: e.context,
                },
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
        if options.json_output is not None:
            json_output = format_json_output(
                success=False,
                command=CLIMessages.CommandNames.MATCH,
                errors=[f"{CLIMessages.Error.UNEXPECTED_ERROR}{e!s}"],
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
        if hasattr(parsing_result, "to_dict"):
            parsing_dict = parsing_result.to_dict()
        elif isinstance(parsing_result, dict):
            parsing_dict = parsing_result
        else:
            # Convert ParsingResult to dict if needed
            parsing_dict = {
                "anime_title": getattr(parsing_result, "title", ""),
                "episode_number": getattr(parsing_result, "episode", ""),
                "release_group": getattr(parsing_result, "release_group", ""),
                "video_resolution": getattr(parsing_result, "quality", ""),
            }
        match_result = await matching_engine.find_match(parsing_dict)

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


def match_command(
    directory: Path = typer.Argument(
        ...,
        help="Directory to match anime files against TMDB database",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    recursive: bool = typer.Option(
        True,
        "--recursive/--no-recursive",
        "-r",
        help="Match files recursively in subdirectories",
    ),
    include_subtitles: bool = typer.Option(
        True,
        "--include-subtitles/--no-include-subtitles",
        help="Include subtitle files in matching",
    ),
    include_metadata: bool = typer.Option(
        True,
        "--include-metadata/--no-include-metadata",
        help="Include metadata files in matching",
    ),
    output_file: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file for match results (JSON format)",
        writable=True,
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output results in JSON format",
    ),
) -> None:
    """
    Match anime files against TMDB database.

    This command takes scanned anime files and matches them against the TMDB database
    to find corresponding TV shows and movies. It uses intelligent matching algorithms
    to handle various naming conventions and provides detailed matching results.

    The matching process includes:
    - Fuzzy string matching for anime titles
    - Episode and season number correlation
    - Quality and release group matching
    - Confidence scoring for match accuracy
    - Fallback strategies for difficult cases

    Matching algorithms:
    - Primary: Exact title and episode matching
    - Secondary: Fuzzy matching with confidence thresholds
    - Fallback: Manual review suggestions

    Examples:
        # Match files in current directory
        anivault match .

        # Match with custom options and save results
        anivault match /path/to/anime --recursive --output match_results.json

        # Match without subtitles (focus on video files only)
        anivault match /path/to/anime --no-include-subtitles

        # Match with verbose output to see matching details
        anivault match /path/to/anime --verbose

        # Match and output results in JSON format
        anivault match /path/to/anime --json
    """

    try:
        # Get CLI context for global options
        context = get_cli_context()

        # Validate arguments using Pydantic model
        from anivault.cli.common.models import DirectoryPath

        match_options = MatchOptions(
            directory=DirectoryPath(path=directory),
            recursive=recursive,
            include_subtitles=include_subtitles,
            include_metadata=include_metadata,
            output=output_file,
            json_output=json_output,
            verbose=bool(context.verbose) if context else False,
        )

        # Call the handler with Pydantic model
        exit_code = handle_match_command(match_options)

        if exit_code != 0:
            raise typer.Exit(exit_code)

    except ValueError as e:
        logger.exception("Validation error")
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e
