"""Scan command handler for AniVault CLI.

This module contains the business logic for the scan command,
separated for better maintainability and single responsibility principle.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import typer

from anivault.cli.common.context import get_cli_context, validate_directory
from anivault.cli.common.models import DirectoryPath, ScanOptions
from anivault.cli.json_formatter import format_json_output
from anivault.cli.progress import create_progress_manager
from anivault.shared.constants import (
    CLIDefaults,
    CLIFormatting,
    CLIHelp,
    CLIMessages,
    CLIOptions,
)
from anivault.shared.constants.file_formats import VideoFormats
from anivault.shared.errors import ApplicationError, InfrastructureError

logger = logging.getLogger(__name__)


def scan_command(
    directory: Path = typer.Argument(
        ...,
        help=CLIHelp.SCAN_DIRECTORY_HELP,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    recursive: bool = typer.Option(
        True,
        CLIOptions.RECURSIVE,
        CLIOptions.RECURSIVE_SHORT,
        help=CLIHelp.SCAN_RECURSIVE_HELP,
    ),
    include_subtitles: bool = typer.Option(
        True,
        CLIOptions.INCLUDE_SUBTITLES,
        help=CLIHelp.SCAN_INCLUDE_SUBTITLES_HELP,
    ),
    include_metadata: bool = typer.Option(
        True,
        CLIOptions.INCLUDE_METADATA,
        help=CLIHelp.SCAN_INCLUDE_METADATA_HELP,
    ),
    output_file: Path | None = typer.Option(
        None,
        CLIOptions.OUTPUT,
        CLIOptions.OUTPUT_SHORT,
        help=CLIHelp.SCAN_OUTPUT_HELP,
        writable=True,
    ),
    json: bool = typer.Option(
        False,
        CLIOptions.JSON,
        help=CLIHelp.SCAN_JSON_HELP,
    ),
) -> None:
    """
    Scan directories for anime files and extract metadata.

    This command recursively scans the specified directory for anime files
    and extracts metadata using anitopy. It can optionally include subtitle
    and metadata files in the scan results.

    The scan process includes:
    - File discovery based on supported extensions
    - Metadata extraction using anitopy parser
    - TMDB API enrichment for additional metadata
    - Progress tracking and error handling

    Supported file extensions: mkv, mp4, avi, mov, wmv, flv, webm, m4v
    Supported subtitle formats: srt, ass, ssa, vtt, smi, sub

    Examples:
        # Scan current directory with default settings
        anivault scan .

        # Scan specific directory with custom options
        anivault scan /path/to/anime --recursive --output results.json

        # Scan without subtitles (faster processing)
        anivault scan /path/to/anime --no-include-subtitles

        # Scan with verbose output for debugging
        anivault scan /path/to/anime --verbose

        # Save results to JSON file
        anivault scan /path/to/anime --output scan_results.json
    """
    try:
        # Validate arguments using Pydantic model
        scan_options = ScanOptions(
            directory=DirectoryPath(path=directory),
            recursive=recursive,
            include_subtitles=include_subtitles,
            include_metadata=include_metadata,
            output=output_file,
            json_output=bool(json),
        )

        # Create args-like object for compatibility
        args = type(
            "Args",
            (),
            {
                "directory": str(scan_options.directory.path),
                "recursive": scan_options.recursive,
                "include_subtitles": scan_options.include_subtitles,
                "include_metadata": scan_options.include_metadata,
                "output_file": str(scan_options.output)
                if scan_options.output
                else None,
                "json": scan_options.json_output,
            },
        )()

        exit_code = _handle_scan_command(args)
        if exit_code != CLIDefaults.EXIT_SUCCESS:
            raise typer.Exit(exit_code)

    except ValueError as e:
        logger.exception("Validation error")
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(CLIDefaults.EXIT_ERROR) from e


def _handle_scan_command(args: Any) -> int:  # noqa: PLR0911
    """Handle the scan command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (CLIDefaults.EXIT_SUCCESS for success, non-zero for error)
    """
    from anivault.shared.constants import CLI

    logger.info(CLI.INFO_COMMAND_STARTED.format(command=CLIMessages.CommandNames.SCAN))

    try:
        import asyncio
        from pathlib import Path

        from rich.console import Console

        from anivault.core.pipeline.main import run_pipeline
        from anivault.services import (
            MetadataEnricher,
            RateLimitStateMachine,
            SemaphoreManager,
            TMDBClient,
            TokenBucketRateLimiter,
        )
        from anivault.shared.constants import (
            CLI,
            QueueConfig,
        )
        from anivault.shared.constants.logging import LogConfig

        console = Console()

        # Validate directory
        try:
            directory = validate_directory(args.directory)
        except ApplicationError as e:
            context = get_cli_context()
            if context and context.is_json_output_enabled():
                json_output = format_json_output(
                    success=False,
                    command="scan",
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
            return CLIDefaults.EXIT_ERROR
        except InfrastructureError as e:
            context = get_cli_context()
            if context and context.is_json_output_enabled():
                json_output = format_json_output(
                    success=False,
                    command="scan",
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
            return CLIDefaults.EXIT_ERROR
        except Exception as e:
            context = get_cli_context()
            if context and context.is_json_output_enabled():
                json_output = format_json_output(
                    success=False,
                    command="scan",
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
            return CLIDefaults.EXIT_ERROR

        # Determine if we should enrich metadata
        enrich_metadata = True  # Default to enrich metadata

        # Only show console output if not in JSON mode
        context = get_cli_context()
        if not (context and context.is_json_output_enabled()):
            console.print(
                CLIFormatting.format_colored_message(
                    f"Scanning directory: {directory}",
                    "info",
                ),
            )
            console.print(
                CLIFormatting.format_colored_message(
                    f"Enriching metadata: {enrich_metadata}",
                    "info",
                ),
            )

        # Create progress manager (disabled for JSON output)
        progress_manager = create_progress_manager(
            disabled=bool(context and context.is_json_output_enabled()),
        )

        try:
            # Run the file processing pipeline with progress display
            # The spinner will show during file discovery phase
            with progress_manager.spinner("Scanning files..."):
                file_results = run_pipeline(
                    root_path=str(directory),
                    extensions=list(VideoFormats.ALL_EXTENSIONS),
                    num_workers=CLIDefaults.DEFAULT_WORKER_COUNT,
                    max_queue_size=QueueConfig.DEFAULT_SIZE,
                )

            context = get_cli_context()
            if not (context and context.is_json_output_enabled()):
                console.print(
                    CLIFormatting.format_colored_message(
                        "✅ File scanning completed!",
                        "success",
                    ),
                )

        except Exception:
            context = get_cli_context()
            if not (context and context.is_json_output_enabled()):
                console.print(
                    CLIFormatting.format_colored_message(
                        "❌ File scanning failed",
                        "error",
                    ),
                )
            raise

        if not file_results:
            context = get_cli_context()
            if context and context.is_json_output_enabled():
                # Return empty results in JSON format
                scan_data = _collect_scan_data([], directory, enrich_metadata)
                json_output = format_json_output(
                    success=True,
                    command="scan",
                    data=scan_data,
                    warnings=["No anime files found in the specified directory"],
                )
                sys.stdout.buffer.write(json_output)
                sys.stdout.buffer.write(b"\n")
                sys.stdout.buffer.flush()
            else:
                console.print(
                    "[yellow]No anime files found in the specified directory[/yellow]",
                )
            return CLIDefaults.EXIT_SUCCESS

        # Enrich metadata if requested
        if enrich_metadata:
            # Initialize TMDB client and enricher
            rate_limiter = TokenBucketRateLimiter(
                capacity=10,  # Default rate limit
                refill_rate=10,  # Default refill rate
            )
            semaphore_manager = SemaphoreManager(
                concurrency_limit=CLIDefaults.DEFAULT_SCAN_CONCURRENCY,
            )  # Default concurrency
            state_machine = RateLimitStateMachine()

            tmdb_client = TMDBClient(
                rate_limiter=rate_limiter,
                semaphore_manager=semaphore_manager,
                state_machine=state_machine,
            )

            enricher = MetadataEnricher(tmdb_client=tmdb_client)

            # Enrich metadata
            async def enrich_metadata_with_progress() -> list[dict[str, Any]]:
                parsing_results = []
                for result in file_results:
                    if "parsing_result" in result:
                        parsing_results.append(result["parsing_result"])

                if not parsing_results:
                    return file_results

                enriched_results = []
                for parsing_result in progress_manager.track(
                    parsing_results,
                    "Enriching metadata...",
                ):
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

        # Check if JSON output is requested
        if args.json:
            # Collect scan statistics for JSON output
            scan_data = _collect_scan_data(enriched_results, directory, enrich_metadata)

            # Output JSON to stdout
            json_output = format_json_output(
                success=True,
                command="scan",
                data=scan_data,
            )
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            # Display results in human-readable format
            _display_results(enriched_results, show_tmdb=enrich_metadata)

            # Save results to file if requested
            if args.output_file:
                import json

                output_path = Path(args.output_file)
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

                with open(output_path, "w", encoding=LogConfig.DEFAULT_ENCODING) as f:
                    json.dump(
                        json_results,
                        f,
                        indent=CLI.INDENT_SIZE,
                        ensure_ascii=False,
                    )

                context = get_cli_context()
                if not (context and context.is_json_output_enabled()):
                    console.print(
                        CLIFormatting.format_colored_message(
                            CLI.SUCCESS_RESULTS_SAVED.format(path=output_path),
                            "success",
                        ),
                    )

        logger.info(CLI.INFO_COMMAND_COMPLETED.format(command="scan"))
        return 0

    except ApplicationError as e:
        context = get_cli_context()
        if context and context.is_json_output_enabled():
            json_output = format_json_output(
                success=False,
                command=CLIMessages.CommandNames.SCAN,
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
            console.print(
                CLIMessages.Error.APPLICATION_ERROR_DURING_SCAN.format(error=e.message),
            )
        logger.exception(
            "Application error in scan command",
            extra={"context": e.context, "error_code": e.code},
        )
        return 1
    except InfrastructureError as e:
        context = get_cli_context()
        if context and context.is_json_output_enabled():
            json_output = format_json_output(
                success=False,
                command=CLIMessages.CommandNames.SCAN,
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
                CLIMessages.Error.INFRASTRUCTURE_ERROR_DURING_SCAN.format(
                    error=e.message,
                ),
            )
            logger.exception(
                "%sin scan command",
                CLIMessages.Error.INFRASTRUCTURE_ERROR,
                extra={
                    CLIMessages.StatusKeys.CONTEXT: e.context,
                    CLIMessages.StatusKeys.ERROR_CODE: e.code,
                },
            )
        return 1
    except Exception as e:
        context = get_cli_context()
        if context and context.is_json_output_enabled():
            json_output = format_json_output(
                success=False,
                command=CLIMessages.CommandNames.SCAN,
                errors=[f"{CLIMessages.Error.UNEXPECTED_ERROR}{e!s}"],
                data={"error_type": type(e).__name__},
            )
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            from rich.console import Console

            console = Console()
            console.print(
                CLIFormatting.format_colored_message(
                    CLI.ERROR_SCAN_FAILED.format(error=e),
                    "error",
                ),
            )
        logger.exception(CLIMessages.Error.APPLICATION_ERROR_IN_SCAN)
        return 1


def _collect_scan_data(
    results: list[dict[str, Any]],
    directory: Path,
    show_tmdb: bool = True,
) -> dict[str, Any]:
    """Collect scan data for JSON output.

    Args:
        results: List of scan results
        directory: Scanned directory path
        show_tmdb: Whether TMDB metadata was enriched

    Returns:
        Dictionary containing scan statistics and file data
    """
    from pathlib import Path

    # Calculate basic statistics
    total_files = len(results)
    total_size = CLIDefaults.DEFAULT_FILE_SIZE
    file_counts_by_extension: dict[str, int] = {}
    scanned_paths = []

    # Process each result
    file_data = []
    for result in results:
        file_path = result.get(
            CLIMessages.Output.FILE_PATH_KEY,
            CLIMessages.Output.UNKNOWN_VALUE,
        )
        parsing_result = result.get("parsing_result")
        enriched_metadata = result.get("enriched_metadata")

        # Add to scanned paths
        scanned_paths.append(file_path)

        # Calculate file size
        try:
            file_size = Path(file_path).stat().st_size
            total_size += file_size
        except (OSError, TypeError):
            file_size = CLIDefaults.DEFAULT_FILE_SIZE

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

        # Add enriched metadata if available
        if show_tmdb and enriched_metadata:
            file_info["enriched_metadata"] = {
                "enrichment_status": enriched_metadata.enrichment_status,
                "match_confidence": enriched_metadata.match_confidence,
                "tmdb_data": enriched_metadata.tmdb_data,
            }

        file_data.append(file_info)

    # Format total size in human-readable format
    def format_size(size_bytes: float) -> str:
        """Convert bytes to human-readable format."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < CLIDefaults.BYTES_PER_KB:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= CLIDefaults.BYTES_PER_KB
        return f"{size_bytes:.1f} PB"

    return {
        "scan_summary": {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_formatted": format_size(total_size),
            "scanned_directory": str(directory),
            "metadata_enriched": show_tmdb,
        },
        "file_statistics": {
            "counts_by_extension": file_counts_by_extension,
            "scanned_paths": scanned_paths,
        },
        "files": file_data,
    }


def _display_results(results: list[dict[str, Any]], show_tmdb: bool = True) -> None:
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
        file_path = result.get(
            CLIMessages.Output.FILE_PATH_KEY,
            CLIMessages.Output.UNKNOWN_VALUE,
        )
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
