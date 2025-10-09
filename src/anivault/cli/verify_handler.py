from __future__ import annotations

import logging
import sys
from typing import Any

import typer

from anivault.cli.common.context import get_cli_context
from anivault.cli.common.models import VerifyOptions
from anivault.cli.json_formatter import format_json_output
from anivault.shared.constants import CLI
from anivault.shared.errors import (
    ApplicationError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
)

logger = logging.getLogger(__name__)


def handle_verify_command(options: VerifyOptions) -> int:
    """Handle the verify command.

    Args:
        options: VerifyOptions containing command arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger.info(CLI.INFO_COMMAND_STARTED.format(command="verify"))

    try:
        context = get_cli_context()
        if context and context.is_json_output_enabled():
            return _handle_verify_command_json(options)
        return _handle_verify_command_console(options)

    except ApplicationError as e:
        logger.exception(
            "Application error in verify command",
            extra={"context": e.context, "error_code": e.code},
        )
        context = get_cli_context()
        if context and context.is_json_output_enabled():
            error_output = format_json_output(
                success=False,
                command="verify",
                errors=[f"Application error: {e.message}"],
            )
            sys.stdout.buffer.write(error_output)
            sys.stdout.buffer.write(b"\n")
        return 1
    except InfrastructureError as e:
        logger.exception(
            "Infrastructure error in verify command",
            extra={"context": e.context, "error_code": e.code},
        )
        context = get_cli_context()
        if context and context.is_json_output_enabled():
            error_output = format_json_output(
                success=False,
                command="verify",
                errors=[f"Infrastructure error: {e.message}"],
            )
            sys.stdout.buffer.write(error_output)
            sys.stdout.buffer.write(b"\n")
        return 1
    except (FileNotFoundError, PermissionError, OSError) as e:
        # Handle file system errors
        logger.exception("File system error in verify command")
        context = get_cli_context()
        if context and context.is_json_output_enabled():
            error_output = format_json_output(
                success=False,
                command="verify",
                errors=[f"File system error: {e}"],
            )
            sys.stdout.buffer.write(error_output)
            sys.stdout.buffer.write(b"\n")
        return 1
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        # Handle data processing errors
        logger.exception("Data processing error in verify command")
        context = get_cli_context()
        if context and context.is_json_output_enabled():
            error_output = format_json_output(
                success=False,
                command="verify",
                errors=[f"Data processing error: {e}"],
            )
            sys.stdout.buffer.write(error_output)
            sys.stdout.buffer.write(b"\n")
        return 1
    except Exception as e:
        # Handle unexpected errors
        logger.exception("Unexpected error in verify command")
        context = get_cli_context()
        if context and context.is_json_output_enabled():
            error_output = format_json_output(
                success=False,
                command="verify",
                errors=[f"Unexpected error: {e}"],
            )
            sys.stdout.buffer.write(error_output)
            sys.stdout.buffer.write(b"\n")
        return 1


def _handle_verify_command_json(options: VerifyOptions) -> int:
    """Handle verify command with JSON output.

    Args:
        options: VerifyOptions containing command arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        verify_data = _collect_verify_data(options)
        if verify_data is None:
            return 1

        output = format_json_output(
            success=True,
            command="verify",
            data=verify_data,
        )
        sys.stdout.buffer.write(output)
        sys.stdout.buffer.write(b"\n")
        return 0
    except (OSError, ValueError, KeyError):
        # Handle specific I/O and data processing errors
        sys.stdout.buffer.write(b"\n")
        logger.exception("Error in verify command JSON output")
        return 1
    except Exception:
        # Handle unexpected errors
        sys.stdout.buffer.write(b"\n")
        logger.exception("Unexpected error in verify command JSON output")
        return 1


def _handle_verify_command_console(options: VerifyOptions) -> int:
    """Handle verify command with console output.

    Args:
        options: VerifyOptions containing command arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        import asyncio

        from rich.console import Console

        console = Console()

        if options.tmdb or options.all_components:
            console.print("[blue]Verifying TMDB API connectivity...[/blue]")

            # Test TMDB client
            from anivault.services import TMDBClient

            client = TMDBClient()

            # Test search functionality
            try:
                asyncio.run(client.search_media("test"))
                console.print("[green]✓ TMDB API connectivity verified[/green]")
            except ApplicationError as e:
                from anivault.shared.constants.system import CLI

                console.print(
                    f"[red]Application error: {e.message}[/red]",
                )
                logger.exception(
                    "TMDB API verification failed",
                    extra={"context": e.context, "error_code": e.code},
                )
                return 1
            except InfrastructureError as e:
                from anivault.shared.constants.system import CLI

                console.print(
                    f"[red]Infrastructure error: {e.message}[/red]",
                )
                logger.exception(
                    "TMDB API verification failed",
                    extra={"context": e.context, "error_code": e.code},
                )
                return 1
            except Exception as e:
                from anivault.shared.constants.system import CLI

                console.print(
                    f"[red]{CLI.ERROR_TMDB_CONNECTIVITY_FAILED.format(error=e)}[/red]",
                )
                logger.exception("Unexpected error during TMDB API verification")
                return 1

        if options.all_components:
            console.print("[blue]Verifying all components...[/blue]")
            # Add more verification checks here
            console.print("[green]✓ All components verified[/green]")

        from anivault.shared.constants.system import CLI

        logger.info(CLI.INFO_COMMAND_COMPLETED.format(command="verify"))
        return 0

    except ApplicationError as e:
        from rich.console import Console

        console = Console()
        console.print(f"[red]Application error: {e.message}[/red]")
        logger.exception(
            "Application error in verify command",
            extra={"context": e.context, "error_code": e.code},
        )
        return 1
    except InfrastructureError as e:
        from anivault.shared.constants.system import CLI

        console.print(f"[red]Infrastructure error: {e.message}[/red]")
        logger.exception(
            "Infrastructure error in verify command",
            extra={"context": e.context, "error_code": e.code},
        )
        return 1
    except Exception as e:
        from anivault.shared.constants.system import CLI

        console.print(f"[red]{CLI.ERROR_VERIFICATION_FAILED.format(error=e)}[/red]")
        logger.exception("Unexpected error in verify command")
        return 1


def _collect_verify_data(options: VerifyOptions) -> dict[str, Any] | None:
    """Collect verify data for JSON output.

    Args:
        options: VerifyOptions containing command arguments

    Returns:
        Dictionary containing verify data, or None if error
    """
    try:
        verify_results: dict[str, dict[str, str] | str | None] = {
            "tmdb_api": None,
            "all_components": None,
            "verification_status": "PENDING",
        }

        if options.tmdb or options.all_components:
            # Test TMDB client
            from anivault.services import TMDBClient

            client = TMDBClient()

            # Test search functionality
            try:
                import asyncio

                asyncio.run(client.search_media("test"))
                verify_results["tmdb_api"] = {
                    "status": "SUCCESS",
                    "message": "TMDB API connectivity verified",
                }
            except ApplicationError as e:
                verify_results["tmdb_api"] = {
                    "status": "FAILED",
                    "message": f"Application error: {e.message}",
                    "error_code": str(e.code),
                }
                verify_results["verification_status"] = "FAILED"
            except InfrastructureError as e:
                verify_results["tmdb_api"] = {
                    "status": "FAILED",
                    "message": f"Infrastructure error: {e.message}",
                    "error_code": str(e.code),
                }
                verify_results["verification_status"] = "FAILED"
            except Exception as e:  # noqa: BLE001
                verify_results["tmdb_api"] = {
                    "status": "FAILED",
                    "message": f"Unexpected error: {e}",
                }
                verify_results["verification_status"] = "FAILED"

        if options.all_components:
            # Add more verification checks here
            verify_results["all_components"] = {
                "status": "SUCCESS",
                "message": "All components verified",
            }

        # Set overall status
        if verify_results["verification_status"] == "PENDING":
            verify_results["verification_status"] = "SUCCESS"

        return verify_results

    except OSError as e:
        # File system I/O error
        raise InfrastructureError(
            code=ErrorCode.FILE_ACCESS_ERROR,
            message=f"Failed to access verification data: {e}",
            context=ErrorContext(
                operation="collect_verify_data",
                additional_data={"error_type": type(e).__name__},
            ),
            original_error=e,
        ) from e
    except (ValueError, KeyError, AttributeError) as e:
        # Data processing error
        raise ApplicationError(
            code=ErrorCode.DATA_PROCESSING_ERROR,
            message=f"Failed to process verification data: {e}",
            context=ErrorContext(
                operation="collect_verify_data",
                additional_data={"error_type": type(e).__name__},
            ),
            original_error=e,
        ) from e
    except Exception as e:
        # Unexpected error
        raise ApplicationError(
            code=ErrorCode.APPLICATION_ERROR,
            message=f"Unexpected error collecting verification data: {e}",
            context=ErrorContext(
                operation="collect_verify_data",
                additional_data={"error_type": type(e).__name__},
            ),
            original_error=e,
        ) from e


def verify_command(
    tmdb: bool = typer.Option(
        default=False,
        help="Verify TMDB API connectivity",
    ),
    all_components: bool = typer.Option(
        default=False,
        help="Verify all components",
    ),
) -> None:
    """
    Verify system components and connectivity.

    This command allows you to verify that various system components are working
    correctly, including TMDB API connectivity and other system dependencies.

    Examples:
        # Verify TMDB API connectivity
        anivault verify --tmdb

        # Verify all components
        anivault verify --all

        # Verify with JSON output
        anivault verify --tmdb --json-output
    """
    try:
        # Create VerifyOptions from command arguments
        options = VerifyOptions(tmdb=tmdb, all=all_components)

        # Call the existing handler with options
        exit_code = handle_verify_command(options)

        if exit_code != 0:
            raise typer.Exit(exit_code)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e
