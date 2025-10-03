"""Organize command handler for AniVault CLI.

This module contains the business logic for the organize command,
separated for better maintainability and single responsibility principle.
"""

import logging
import sys
from pathlib import Path
from typing import Any

from anivault.cli.json_formatter import format_json_output
from anivault.cli.progress import create_progress_manager
from anivault.shared.constants import CLI
from anivault.shared.errors import (
    ApplicationError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
)

logger = logging.getLogger(__name__)


def handle_organize_command(args: Any) -> int:
    """Handle the organize command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger.info(CLI.INFO_COMMAND_STARTED.format(command="organize"))

    try:
        console = _setup_organize_console()
        directory = _validate_organize_directory(args, console)
        if directory is None:
            return 1

        scanned_files = _get_scanned_files(args, directory, console)
        if not scanned_files:
            if hasattr(args, "json") and args.json:
                # Return empty results in JSON format
                organize_data = _collect_organize_data([], args, is_dry_run=False)
                json_output = format_json_output(
                    success=True,
                    command="organize",
                    data=organize_data,
                    warnings=["No anime files found to organize"],
                )
                sys.stdout.buffer.write(json_output)
                sys.stdout.buffer.write(b"\n")
                sys.stdout.buffer.flush()
            return 0

        # Check if enhanced organization is requested
        if hasattr(args, "enhanced") and args.enhanced:
            plan = _generate_enhanced_organization_plan(scanned_files, args)
        else:
            plan = _generate_organization_plan(scanned_files)
        return _execute_organization_plan(plan, args, console)

    except ApplicationError as e:
        if hasattr(args, "json") and args.json:
            json_output = format_json_output(
                success=False,
                command="organize",
                errors=[f"Application error: {e.message}"],
                data={"error_code": e.code, "context": e.context},
            )
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            from rich.console import Console

            console = Console()
            console.print(
                f"[red]Application error during organization: {e.message}[/red]",
            )
        logger.exception(
            "Application error in organize command",
            extra={"context": e.context, "error_code": e.code},
        )
        return 1
    except InfrastructureError as e:
        if hasattr(args, "json") and args.json:
            json_output = format_json_output(
                success=False,
                command="organize",
                errors=[f"Infrastructure error: {e.message}"],
                data={"error_code": e.code, "context": e.context},
            )
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            from rich.console import Console

            console = Console()
            console.print(
                f"[red]Infrastructure error during organization: {e.message}[/red]",
            )
        logger.exception(
            "Infrastructure error in organize command",
            extra={"context": e.context, "error_code": e.code},
        )
        return 1
    except Exception as e:
        if hasattr(args, "json") and args.json:
            json_output = format_json_output(
                success=False,
                command="organize",
                errors=[f"Unexpected error: {e!s}"],
                data={"error_type": type(e).__name__},
            )
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            from rich.console import Console

            console = Console()
            console.print(f"[red]Unexpected error during organization: {e}[/red]")
        logger.exception("Unexpected error in organize command")
        return 1


def _setup_organize_console() -> Any:
    """Setup console for organize command."""
    from rich.console import Console

    return Console()


def _validate_organize_directory(args: Any, console: Any) -> Any:
    """Validate directory for organize command."""
    try:
        from anivault.cli.common.context import validate_directory

        directory = validate_directory(args.directory)
        if not (hasattr(args, "json") and args.json):
            console.print(f"[green]Organizing files in: {directory}[/green]")
        return directory
    except ApplicationError as e:
        if hasattr(args, "json") and args.json:
            json_output = format_json_output(
                success=False,
                command="organize",
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
        return None
    except InfrastructureError as e:
        if hasattr(args, "json") and args.json:
            json_output = format_json_output(
                success=False,
                command="organize",
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
        return None
    except Exception as e:
        if hasattr(args, "json") and args.json:
            json_output = format_json_output(
                success=False,
                command="organize",
                errors=[f"Unexpected error: {e!s}"],
                data={"error_type": type(e).__name__},
            )
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            console.print(f"[red]Unexpected error: {e}[/red]")
        logger.exception("Unexpected error during directory validation")
        return None


def _get_scanned_files(args: Any, directory: Any, console: Any) -> Any:
    """Get scanned files for organization."""
    try:
        from anivault.core.pipeline.main import run_pipeline
        from anivault.shared.constants import QueueConfig, WorkerConfig

        # Create progress manager (disabled for JSON output)
        progress_manager = create_progress_manager(
            disabled=(hasattr(args, "json") and args.json),
        )

        # Scan files with progress indication
        with progress_manager.spinner("Scanning files..."):
            file_results = run_pipeline(
                root_path=str(directory),
                extensions=args.extensions,
                num_workers=WorkerConfig.DEFAULT,
                max_queue_size=QueueConfig.DEFAULT_SIZE,
            )

        if not file_results:
            if not (hasattr(args, "json") and args.json):
                console.print(
                    "[yellow]No anime files found in the specified directory[/yellow]",
                )
            return []

        # Convert file results to ScannedFile objects
        from pathlib import Path

        from anivault.core.models import ScannedFile

        scanned_files = []
        for result in file_results:
            if "parsing_result" in result:
                scanned_file = ScannedFile(
                    file_path=Path(result["file_path"]),
                    metadata=result["parsing_result"],
                )
                scanned_files.append(scanned_file)

        if not scanned_files:
            if not (hasattr(args, "json") and args.json):
                console.print("[yellow]No valid anime files found to organize[/yellow]")
            return []

        return scanned_files

    except ApplicationError as e:
        if not (hasattr(args, "json") and args.json):
            console.print(
                f"[red]Application error during file scanning: {e.message}[/red]",
            )
        logger.exception(
            "File scanning failed",
            extra={"context": e.context, "error_code": e.code},
        )
        raise ApplicationError(
            ErrorCode.CLI_PIPELINE_EXECUTION_FAILED,
            "Failed to scan files for organization",
            ErrorContext(
                operation="get_scanned_files",
                additional_data={"directory": str(directory)},
            ),
            original_error=e,
        ) from e
    except InfrastructureError as e:
        if not (hasattr(args, "json") and args.json):
            console.print(
                f"[red]Infrastructure error during file scanning: {e.message}[/red]",
            )
        logger.exception(
            "File scanning failed",
            extra={"context": e.context, "error_code": e.code},
        )
        raise InfrastructureError(
            ErrorCode.CLI_PIPELINE_EXECUTION_FAILED,
            "Failed to scan files for organization",
            ErrorContext(
                operation="get_scanned_files",
                additional_data={"directory": str(directory)},
            ),
            original_error=e,
        ) from e
    except Exception as e:
        if not (hasattr(args, "json") and args.json):
            console.print(f"[red]Unexpected error during file scanning: {e}[/red]")
        logger.exception("Unexpected error during file scanning")
        raise ApplicationError(
            ErrorCode.CLI_PIPELINE_EXECUTION_FAILED,
            "Failed to scan files for organization",
            ErrorContext(
                operation="get_scanned_files",
                additional_data={"directory": str(directory)},
            ),
            original_error=e,
        ) from e


def _generate_organization_plan(scanned_files: Any) -> Any:
    """Generate organization plan."""
    try:
        from pathlib import Path

        from anivault.core.log_manager import OperationLogManager
        from anivault.core.organizer import FileOrganizer

        log_manager = OperationLogManager(Path.cwd())
        organizer = FileOrganizer(log_manager=log_manager)
        return organizer.generate_plan(scanned_files)

    except ApplicationError as e:
        logger.exception(
            "Organization plan generation failed",
            extra={"context": e.context, "error_code": e.code},
        )
        raise ApplicationError(
            ErrorCode.CLI_FILE_ORGANIZATION_FAILED,
            "Failed to generate organization plan",
            ErrorContext(
                operation="generate_organization_plan",
                additional_data={"file_count": len(scanned_files)},
            ),
            original_error=e,
        ) from e
    except InfrastructureError as e:
        logger.exception(
            "Organization plan generation failed",
            extra={"context": e.context, "error_code": e.code},
        )
        raise InfrastructureError(
            ErrorCode.CLI_FILE_ORGANIZATION_FAILED,
            "Failed to generate organization plan",
            ErrorContext(
                operation="generate_organization_plan",
                additional_data={"file_count": len(scanned_files)},
            ),
            original_error=e,
        ) from e
    except Exception as e:
        logger.exception("Unexpected error during organization plan generation")
        raise ApplicationError(
            ErrorCode.CLI_FILE_ORGANIZATION_FAILED,
            "Failed to generate organization plan",
            ErrorContext(
                operation="generate_organization_plan",
                additional_data={"file_count": len(scanned_files)},
            ),
            original_error=e,
        ) from e


def _execute_organization_plan(plan: Any, args: Any, console: Any) -> int:
    """Execute organization plan."""
    if args.dry_run:
        if hasattr(args, "json") and args.json:
            # Output dry run plan in JSON format
            organize_data = _collect_organize_data(plan, args, is_dry_run=True)
            json_output = format_json_output(
                success=True,
                command="organize",
                data=organize_data,
            )
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            _print_dry_run_plan_impl(plan, console)
        logger.info(CLI.INFO_COMMAND_COMPLETED.format(command="organize"))
        return 0

    if not (hasattr(args, "json") and args.json):
        _print_execution_plan_impl(plan, console)

    if not args.yes and not (hasattr(args, "json") and args.json):
        if not _confirm_organization(console):
            return 0

    return _perform_organization(plan, args)


def _confirm_organization(console: Any) -> bool:
    """Ask for confirmation."""
    try:
        from rich.prompt import Confirm

        if not Confirm.ask("Do you want to proceed?"):
            console.print("[yellow]Operation cancelled.[/yellow]")
            return False
        return True
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled.[/yellow]")
        return False


def _perform_organization(plan: Any, args: Any) -> int:
    """Perform the actual organization."""
    try:
        from datetime import datetime
        from pathlib import Path

        from rich.console import Console

        from anivault.core.log_manager import OperationLogManager
        from anivault.core.organizer import FileOrganizer

        console = Console()
        log_manager = OperationLogManager(Path.cwd())
        organizer = FileOrganizer(log_manager=log_manager)

        operation_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create progress manager (disabled for JSON output)
        progress_manager = create_progress_manager(
            disabled=(hasattr(args, "json") and args.json),
        )

        # Execute organization with progress indication
        with progress_manager.spinner("Organizing files..."):
            moved_files = organizer.execute_plan(plan, operation_id)

        if hasattr(args, "json") and args.json:
            # Output results in JSON format
            organize_data = _collect_organize_data(
                plan,
                args,
                moved_files=moved_files,
                operation_id=operation_id,
            )
            json_output = format_json_output(
                success=True,
                command="organize",
                data=organize_data,
            )
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        elif moved_files:
            console.print(
                f"[green]Successfully organized {len(moved_files)} files[/green]",
            )
            try:
                saved_log_path = log_manager.save_plan(plan)
                console.print(
                    f"[grey62]Operation logged to: {saved_log_path}[/grey62]",
                )
            except Exception as e:
                console.print(
                    f"[bold yellow]Warning: Could not save operation log: "
                    f"{e}[/bold yellow]",
                )
        else:
            console.print("[yellow]No files were moved[/yellow]")

        logger.info(CLI.INFO_COMMAND_COMPLETED.format(command="organize"))
        return 0

    except ApplicationError as e:
        logger.exception(
            "Organization execution failed",
            extra={"context": e.context, "error_code": e.code},
        )
        raise ApplicationError(
            ErrorCode.CLI_FILE_ORGANIZATION_FAILED,
            "Failed to execute organization plan",
            ErrorContext(
                operation="perform_organization",
                additional_data={"plan_size": len(plan)},
            ),
            original_error=e,
        ) from e
    except InfrastructureError as e:
        logger.exception(
            "Organization execution failed",
            extra={"context": e.context, "error_code": e.code},
        )
        raise InfrastructureError(
            ErrorCode.CLI_FILE_ORGANIZATION_FAILED,
            "Failed to execute organization plan",
            ErrorContext(
                operation="perform_organization",
                additional_data={"plan_size": len(plan)},
            ),
            original_error=e,
        ) from e
    except Exception as e:
        logger.exception("Unexpected error during organization execution")
        raise ApplicationError(
            ErrorCode.CLI_FILE_ORGANIZATION_FAILED,
            "Failed to execute organization plan",
            ErrorContext(
                operation="perform_organization",
                additional_data={"plan_size": len(plan)},
            ),
            original_error=e,
        ) from e


def _collect_organize_data(
    plan: Any,
    args: Any,
    is_dry_run: bool = False,
    moved_files: Any = None,
    operation_id: Any = None,
) -> dict[str, Any]:
    """Collect organize data for JSON output.

    Args:
        plan: Organization plan
        args: Command line arguments
        is_dry_run: Whether this is a dry run
        moved_files: List of moved files (for actual execution)
        operation_id: Operation ID (for actual execution)

    Returns:
        Dictionary containing organize statistics and plan data
    """
    from pathlib import Path

    # Calculate basic statistics
    total_operations = len(plan)
    successful_moves = len(moved_files) if moved_files else 0

    # Process each operation
    operations_data = []
    for operation in plan:
        source_path = str(operation.source_file.file_path)
        destination_path = str(operation.destination_path)

        # Calculate file size
        try:
            file_size = Path(source_path).stat().st_size
        except (OSError, TypeError):
            file_size = 0

        operation_info = {
            "source_path": source_path,
            "destination_path": destination_path,
            "file_name": Path(source_path).name,
            "file_size": file_size,
            "file_extension": Path(source_path).suffix.lower(),
        }

        # Add parsing result if available
        if (
            hasattr(operation.source_file, "parsing_result")
            and operation.source_file.parsing_result
        ):
            parsing_result = operation.source_file.parsing_result
            operation_info["parsing_result"] = {
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

        operations_data.append(operation_info)

    # Format total size in human-readable format
    def format_size(size_bytes: float) -> str:
        """Convert bytes to human-readable format."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    # Calculate total size - boundary conversion from Any to int
    total_size = 0
    for op in operations_data:
        # Boundary: Accept Any from dict.get(), immediately convert to safe types
        raw_file_size: Any = op.get("file_size", 0)

        if isinstance(raw_file_size, int):
            total_size += raw_file_size
        elif isinstance(raw_file_size, str):
            try:
                total_size += int(raw_file_size)
            except (ValueError, TypeError):
                pass
        # Skip other types silently - boundary Any properly handled

    return {
        "organize_summary": {
            "total_operations": total_operations,
            "successful_moves": successful_moves,
            "is_dry_run": is_dry_run,
            "operation_id": operation_id,
            "total_size_bytes": total_size,
            "total_size_formatted": format_size(total_size),
            "success_rate": (
                (successful_moves / total_operations * 100)
                if total_operations > 0
                else 0
            ),
        },
        "operations": operations_data,
    }


def _print_dry_run_plan_impl(plan: Any, console: Any) -> None:
    """Print dry run plan."""
    console.print("[bold blue]Dry Run - Organization Plan:[/bold blue]")
    console.print()

    for operation in plan:
        source = operation.source_file.file_path
        destination = operation.destination_path
        console.print(f"[yellow]Would move:[/yellow] {source}")
        console.print(f"[green]To:[/green] {destination}")
        console.print()

    console.print(f"[bold]Total operations: {len(plan)}[/bold]")


def _print_execution_plan_impl(plan: Any, console: Any) -> None:
    """Print execution plan."""
    console.print("[bold blue]Organization Plan:[/bold blue]")
    console.print()

    for operation in plan:
        source = operation.source_file.file_path
        destination = operation.destination_path
        console.print(f"[yellow]Will move:[/yellow] {source}")
        console.print(f"[green]To:[/green] {destination}")
        console.print()


def _generate_enhanced_organization_plan(
    scanned_files: list[Any],
    args: Any,
) -> list[Any]:
    """Generate enhanced organization plan with grouping, Korean titles, and resolution-based sorting.

    Args:
        scanned_files: List of scanned files to organize
        args: Command line arguments

    Returns:
        List of file operations for enhanced organization

    Raises:
        ApplicationError: If plan generation fails
    """
    try:
        from anivault.core.file_grouper import FileGrouper
        from anivault.core.resolution_detector import ResolutionDetector
        from anivault.core.subtitle_matcher import SubtitleMatcher
        from anivault.services.tmdb_client import TMDBClient
        from anivault.shared.constants import Language

        # Initialize components
        grouper = FileGrouper(similarity_threshold=0.7)
        resolution_detector = ResolutionDetector()
        subtitle_matcher = SubtitleMatcher()

        # Use Korean language for TMDB if enhanced mode
        tmdb_client = TMDBClient(language=Language.KOREAN)  # noqa: F841

        # Group files by similarity
        file_groups = grouper.group_files(scanned_files)

        operations = []

        for group_key, group_files in file_groups.items():
            # Find highest resolution file in group
            best_file = resolution_detector.find_highest_resolution(group_files)
            if not best_file:
                continue

            # Get TMDB metadata for Korean title
            # Fallback to group key for now
            korean_title = group_key  # Fallback to group key for now

            # Find matching subtitles
            subtitles = subtitle_matcher.find_matching_subtitles(
                best_file,
                best_file.file_path.parent,
            )

            # Generate destination paths
            destination_base = getattr(args, "destination", "Anime")
            high_res_path = (
                Path(destination_base)
                / korean_title
                / f"Season {best_file.metadata.season or 1:02d}"
            )
            low_res_path = (
                Path(destination_base)
                / "low_res"
                / korean_title
                / f"Season {best_file.metadata.season or 1:02d}"
            )

            # Create operations for highest resolution file + subtitles
            operations.append(
                {
                    "source": best_file.file_path,
                    "destination": high_res_path / best_file.file_path.name,
                    "type": "move",
                    "is_highest_resolution": True,
                },
            )

            # Add subtitle operations
            for subtitle in subtitles:
                operations.append(
                    {
                        "source": subtitle,
                        "destination": high_res_path / subtitle.name,
                        "type": "move",
                        "is_subtitle": True,
                    },
                )

            # Create operations for lower resolution files
            for file in group_files:
                if file != best_file:
                    operations.append(
                        {
                            "source": file.file_path,
                            "destination": low_res_path / file.file_path.name,
                            "type": "move",
                            "is_highest_resolution": False,
                        },
                    )

        return operations

    except Exception as e:
        logger.exception("Failed to generate enhanced organization plan")
        raise ApplicationError(
            code=ErrorCode.ORGANIZATION_PLAN_FAILED,
            message=f"Enhanced organization plan generation failed: {e!s}",
            context=ErrorContext(operation="generate_enhanced_organization_plan"),
            original_error=e,
        ) from e
