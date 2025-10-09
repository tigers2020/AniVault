"""Organize command handler for AniVault CLI.

This module contains the business logic for the organize command,
separated for better maintainability and single responsibility principle.
"""

import logging
import sys
from pathlib import Path
from typing import Any

import typer

from anivault.cli.common.context import get_cli_context
from anivault.cli.common.error_decorator import handle_cli_errors
from anivault.cli.common.models import OrganizeOptions
from anivault.cli.json_formatter import format_json_output
from anivault.cli.progress import create_progress_manager
from anivault.shared.constants import CLI
from anivault.shared.constants.cli import CLIFormatting, CLIMessages
from anivault.shared.errors import (
    ApplicationError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
)

logger = logging.getLogger(__name__)


def handle_organize_command(options: OrganizeOptions) -> int:
    """Handle the organize command.

    Args:
        options: Validated organize command options

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger.info(
        CLI.INFO_COMMAND_STARTED.format(command=CLIMessages.CommandNames.ORGANIZE),
    )

    try:
        console = _setup_organize_console()

        # Validate directory (raises exception on error)
        directory = _validate_organize_directory(options, console)

        scanned_files = _get_scanned_files(options, directory, console)
        if not scanned_files:
            if options.json_output:
                # Return empty results in JSON format
                organize_data = _collect_organize_data([], options, is_dry_run=False)
                json_output = format_json_output(
                    success=True,
                    command=CLIMessages.CommandNames.ORGANIZE,
                    data=organize_data,
                    warnings=["No anime files found to organize"],
                )
                sys.stdout.buffer.write(json_output)
                sys.stdout.buffer.write(b"\n")
                sys.stdout.buffer.flush()
            return 0

        # Check if enhanced organization is requested
        if options.enhanced:
            plan = _generate_enhanced_organization_plan(scanned_files, options)
        else:
            plan = _generate_organization_plan(scanned_files)
        return _execute_organization_plan(plan, options, console)

    except ApplicationError as e:
        logger.exception(
            "%sin organize command",
            CLIMessages.Error.APPLICATION_ERROR,
            extra={
                CLIMessages.StatusKeys.CONTEXT: e.context,
                CLIMessages.StatusKeys.ERROR_CODE: e.code,
            },
        )
        if options.json_output:
            json_output = format_json_output(
                success=False,
                command=CLIMessages.CommandNames.ORGANIZE,
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
            from rich.console import Console

            console = Console()
            console.print(
                CLIFormatting.format_colored_message(
                    f"Application error during organization: {e.message}",
                    "error",
                ),
            )
        return 1
    except InfrastructureError as e:
        logger.exception(
            "%sin organize command",
            CLIMessages.Error.INFRASTRUCTURE_ERROR,
            extra={
                CLIMessages.StatusKeys.CONTEXT: e.context,
                CLIMessages.StatusKeys.ERROR_CODE: e.code,
            },
        )
        if options.json_output:
            json_output = format_json_output(
                success=False,
                command=CLIMessages.CommandNames.ORGANIZE,
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
            from rich.console import Console

            console = Console()
            console.print(
                CLIFormatting.format_colored_message(
                    f"Infrastructure error during organization: {e.message}",
                    "error",
                ),
            )
        return 1
    except Exception as e:
        logger.exception("%sin organize command", CLIMessages.Error.UNEXPECTED_ERROR)
        if options.json_output:
            json_output = format_json_output(
                success=False,
                command=CLIMessages.CommandNames.ORGANIZE,
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
                    f"Unexpected error during organization: {e}",
                    "error",
                ),
            )
        return 1


def _setup_organize_console() -> Any:
    """Setup console for organize command."""
    from rich.console import Console

    return Console()


def _validate_organize_directory(options: OrganizeOptions, console: Any) -> Path:
    """Validate directory for organize command.

    Args:
        options: Validated organize options
        console: Rich console for output

    Returns:
        Validated directory path

    Raises:
        ApplicationError: If directory validation fails
        InfrastructureError: If directory access fails
    """
    from anivault.cli.common.context import validate_directory

    try:
        directory = validate_directory(str(options.directory))
        if not options.json_output:
            console.print(
                CLIFormatting.format_colored_message(
                    f"Organizing files in: {directory}",
                    "success",
                ),
            )
        return directory
    except (ApplicationError, InfrastructureError):
        # Re-raise AniVault errors as-is (caller will handle UI/logging)
        raise
    except Exception as e:
        # Wrap unexpected errors
        raise InfrastructureError(
            code=ErrorCode.FILE_ACCESS_ERROR,
            message=f"Unexpected error validating directory: {e}",
            context=ErrorContext(
                operation="validate_organize_directory",
                additional_data={
                    "directory": str(options.directory),
                    "error_type": type(e).__name__,
                },
            ),
            original_error=e,
        ) from e


@handle_cli_errors(operation="get_scanned_files", command_name="organize")
def _get_scanned_files(options: OrganizeOptions, directory: Any, console: Any) -> Any:
    """Get scanned files for organization."""
    from anivault.core.models import ScannedFile
    from anivault.core.pipeline.main import run_pipeline
    from anivault.shared.constants import QueueConfig, WorkerConfig

    # Create progress manager (disabled for JSON output)
    progress_manager = create_progress_manager(
        disabled=options.json_output,
    )

    # Scan files with progress indication
    with progress_manager.spinner(CLIMessages.Info.SCANNING_FILES):
        file_results = run_pipeline(
            root_path=str(directory),
            extensions=options.extensions.split(","),
            num_workers=WorkerConfig.DEFAULT,
            max_queue_size=QueueConfig.DEFAULT_SIZE,
        )

    if not file_results:
        if not options.json_output:
            console.print(
                CLIFormatting.format_colored_message(
                    CLIMessages.Info.NO_ANIME_FILES_FOUND,
                    "warning",
                ),
            )
        return []

    # Convert file results to ScannedFile objects
    scanned_files = []
    for result in file_results:
        if CLIMessages.StatusKeys.PARSING_RESULT in result:
            scanned_file = ScannedFile(
                file_path=Path(result[CLIMessages.StatusKeys.FILE_PATH]),
                metadata=result[CLIMessages.StatusKeys.PARSING_RESULT],
            )
            scanned_files.append(scanned_file)

    if not scanned_files:
        if not options.json_output:
            console.print(
                CLIFormatting.format_colored_message(
                    "No valid anime files found to organize",
                    "warning",
                ),
            )
        return []

    return scanned_files


@handle_cli_errors(operation="generate_organization_plan", command_name="organize")
def _generate_organization_plan(scanned_files: Any) -> Any:
    """Generate organization plan."""
    from anivault.core.log_manager import OperationLogManager
    from anivault.core.organizer import FileOrganizer

    log_manager = OperationLogManager(Path.cwd())
    organizer = FileOrganizer(log_manager=log_manager)
    return organizer.generate_plan(scanned_files)


def _execute_organization_plan(
    plan: Any,
    options: OrganizeOptions,
    console: Any,
) -> int:
    """Execute organization plan."""
    if options.dry_run:
        if options.json_output:
            # Output dry run plan in JSON format
            organize_data = _collect_organize_data(plan, options, is_dry_run=True)
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

    if not options.json_output:
        _print_execution_plan_impl(plan, console)

    if not options.yes and not options.json_output:
        if not _confirm_organization(console):
            return 0

    return _perform_organization(plan, options)


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


@handle_cli_errors(operation="perform_organization", command_name="organize")
def _perform_organization(plan: Any, options: OrganizeOptions) -> int:
    """Perform the actual organization."""
    from datetime import datetime

    from rich.console import Console

    from anivault.core.log_manager import OperationLogManager
    from anivault.core.organizer import FileOrganizer

    console = Console()
    log_manager = OperationLogManager(Path.cwd())
    organizer = FileOrganizer(log_manager=log_manager)

    operation_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create progress manager (disabled for JSON output)
    progress_manager = create_progress_manager(
        disabled=options.json_output,
    )

    # Execute organization with progress indication
    with progress_manager.spinner("Organizing files..."):
        moved_files = organizer.execute_plan(plan, operation_id)

    if options.json_output:
        # Output results in JSON format
        organize_data = _collect_organize_data(
            plan,
            options,
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
        except Exception as e:  # noqa: BLE001
            console.print(
                f"[bold yellow]Warning: Could not save operation log: "
                f"{e}[/bold yellow]",
            )
    else:
        console.print("[yellow]No files were moved[/yellow]")

    logger.info(CLI.INFO_COMMAND_COMPLETED.format(command="organize"))
    return 0


def _collect_organize_data(
    plan: Any,
    options: OrganizeOptions,
    is_dry_run: bool = False,
    moved_files: Any = None,
    operation_id: Any = None,
) -> dict[str, Any]:
    """Collect organize data for JSON output.

    Args:
        plan: Organization plan
        options: Organize command options
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
            except (ValueError, TypeError) as e:
                logger.warning(
                    "Invalid file size value in operation data: %s (type: %s)",
                    raw_file_size,
                    type(raw_file_size).__name__,
                    extra={"error": str(e)},
                )
        # Skip other types with warning
        elif raw_file_size is not None:
            logger.warning(
                "Unexpected file size type in operation data: %s",
                type(raw_file_size).__name__,
            )

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


@handle_cli_errors(
    operation="generate_enhanced_organization_plan",
    command_name="organize",
)
def _generate_enhanced_organization_plan(
    scanned_files: list[Any],
    options: OrganizeOptions,
) -> list[Any]:
    """Generate enhanced organization plan with grouping, Korean titles, and resolution-based sorting.

    Args:
        scanned_files: List of scanned files to organize
        options: Organize command options

    Returns:
        List of file operations for enhanced organization
    """
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
        destination_base = options.destination if options.destination else "Anime"
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


def organize_command(
    directory: Path = typer.Argument(
        ...,
        help="Directory containing scanned and matched anime files to organize",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be organized without actually moving files",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompts and proceed with organization",
    ),
    enhanced: bool = typer.Option(
        False,
        "--enhanced",
        help="Use enhanced organization with grouping and Korean titles",
    ),
    destination: str = typer.Option(
        "Anime",
        "--destination",
        "-d",
        help="Destination directory for organized files",
    ),
    extensions: str = typer.Option(
        "mkv,mp4,avi,mov,wmv,flv,webm,m4v",
        "--extensions",
        help="Comma-separated list of video file extensions to process",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output results in JSON format",
    ),
) -> None:
    """
    Organize anime files into a structured directory layout.

    This command takes scanned and matched anime files and organizes them
    into a clean directory structure based on the TMDB metadata. It can
    create series folders, season subfolders, and rename files consistently.

    Organization features:
    - Creates hierarchical directory structure (Series/Season/Episodes)
    - Renames files with consistent naming convention
    - Preserves original files or creates hard links/copies
    - Supports enhanced organization with Korean titles
    - Handles multiple file formats and extensions
    - Provides dry-run mode for safe preview

    Directory structure example:
        Anime/
        └── Attack on Titan/
            ├── Season 1/
            │   ├── Attack on Titan - S01E01.mkv
            │   └── Attack on Titan - S01E02.mkv
            └── Season 2/
                ├── Attack on Titan - S02E01.mkv
                └── Attack on Titan - S02E02.mkv

    Examples:
        # Organize files in current directory (with confirmation)
        anivault organize .

        # Preview what would be organized without making changes
        anivault organize . --dry-run

        # Organize without confirmation prompts
        anivault organize . --yes

        # Use enhanced organization with Korean titles
        anivault organize . --enhanced

        # Organize to custom destination directory
        anivault organize . --destination "My Anime Collection"

        # Process only specific file extensions
        anivault organize . --extensions "mkv,mp4"

        # Combine multiple options
        anivault organize . --enhanced --destination "Anime" --yes
    """
    try:
        # Get CLI context for global options
        context = get_cli_context()

        # Parse extensions string
        extensions_list = [ext.strip() for ext in extensions.split(",")]

        # Validate arguments using Pydantic model
        from anivault.cli.common.models import DirectoryPath

        organize_options = OrganizeOptions(
            directory=DirectoryPath(path=directory),
            dry_run=dry_run,
            yes=yes,
            enhanced=enhanced,
            destination=destination,
            extensions=",".join(extensions_list),
            json_output=json_output,
            verbose=bool(context.verbose) if context else False,
        )

        # Call the handler with Pydantic model
        exit_code = handle_organize_command(organize_options)

        if exit_code != 0:
            raise typer.Exit(exit_code)

    except ValueError as e:
        logger.exception("Validation error")
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e
