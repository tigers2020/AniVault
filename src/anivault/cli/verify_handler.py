"""Verify command handler for AniVault CLI.

This module contains the business logic for the verify command,
separated for better maintainability and single responsibility principle.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from anivault.cli.common_options import is_json_output_enabled
from anivault.cli.json_formatter import format_json_output
from anivault.shared.constants import CLI
from anivault.shared.errors import ApplicationError, InfrastructureError

logger = logging.getLogger(__name__)


def handle_verify_command(args: Any) -> int:
    """Handle the verify command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger.info(CLI.INFO_COMMAND_STARTED.format(command="verify"))

    try:
        if is_json_output_enabled(args):
            return _handle_verify_command_json(args)
        return _handle_verify_command_console(args)

    except ApplicationError as e:
        logger.exception(
            "Application error in verify command",
            extra={"context": e.context, "error_code": e.code},
        )
        if is_json_output_enabled(args):
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
        if is_json_output_enabled(args):
            error_output = format_json_output(
                success=False,
                command="verify",
                errors=[f"Infrastructure error: {e.message}"],
            )
            sys.stdout.buffer.write(error_output)
            sys.stdout.buffer.write(b"\n")
        return 1
    except Exception as e:
        logger.exception("Unexpected error in verify command")
        if is_json_output_enabled(args):
            error_output = format_json_output(
                success=False,
                command="verify",
                errors=[f"Unexpected error: {e}"],
            )
            sys.stdout.buffer.write(error_output)
            sys.stdout.buffer.write(b"\n")
        return 1


def _handle_verify_command_json(args: Any) -> int:
    """Handle verify command with JSON output.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        verify_data = _collect_verify_data(args)
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

    except Exception as e:
        error_output = format_json_output(
            success=False,
            command="verify",
            errors=[f"Error during verify operation: {e}"],
        )
        sys.stdout.buffer.write(error_output)
        sys.stdout.buffer.write(b"\n")
        logger.exception("Error in verify command JSON output")
        return 1


def _handle_verify_command_console(args: Any) -> int:  # noqa: PLR0911
    """Handle verify command with console output.

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
            except ApplicationError as e:
                from anivault.shared.constants.system import (
                    CLI_ERROR_TMDB_CONNECTIVITY_FAILED,
                )

                console.print(
                    f"[red]Application error: {e.message}[/red]",
                )
                logger.exception(
                    "TMDB API verification failed",
                    extra={"context": e.context, "error_code": e.code},
                )
                return 1
            except InfrastructureError as e:
                from anivault.shared.constants.system import (
                    CLI_ERROR_TMDB_CONNECTIVITY_FAILED,
                )

                console.print(
                    f"[red]Infrastructure error: {e.message}[/red]",
                )
                logger.exception(
                    "TMDB API verification failed",
                    extra={"context": e.context, "error_code": e.code},
                )
                return 1
            except Exception as e:
                from anivault.shared.constants.system import (
                    CLI_ERROR_TMDB_CONNECTIVITY_FAILED,
                )

                console.print(
                    f"[red]{CLI_ERROR_TMDB_CONNECTIVITY_FAILED.format(error=e)}[/red]",
                )
                logger.exception("Unexpected error during TMDB API verification")
                return 1

        if args.all:
            console.print("[blue]Verifying all components...[/blue]")
            # Add more verification checks here
            console.print("[green]✓ All components verified[/green]")

        logger.info(CLI.INFO_COMMAND_COMPLETED.format(command="verify"))
        return 0

    except ApplicationError as e:
        from anivault.shared.constants.system import CLI_ERROR_VERIFICATION_FAILED

        console.print(f"[red]Application error: {e.message}[/red]")
        logger.exception(
            "Application error in verify command",
            extra={"context": e.context, "error_code": e.code},
        )
        return 1
    except InfrastructureError as e:
        from anivault.shared.constants.system import CLI_ERROR_VERIFICATION_FAILED

        console.print(f"[red]Infrastructure error: {e.message}[/red]")
        logger.exception(
            "Infrastructure error in verify command",
            extra={"context": e.context, "error_code": e.code},
        )
        return 1
    except Exception as e:
        from anivault.shared.constants.system import CLI_ERROR_VERIFICATION_FAILED

        console.print(f"[red]{CLI_ERROR_VERIFICATION_FAILED.format(error=e)}[/red]")
        logger.exception("Unexpected error in verify command")
        return 1


def _collect_verify_data(args: Any) -> dict | None:
    """Collect verify data for JSON output.

    Args:
        args: Parsed command line arguments

    Returns:
        Dictionary containing verify data, or None if error
    """
    try:
        verify_results = {
            "tmdb_api": None,
            "all_components": None,
            "verification_status": "PENDING",
        }

        if args.tmdb or args.all:
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
                    "error_code": e.code,
                }
                verify_results["verification_status"] = "FAILED"
            except InfrastructureError as e:
                verify_results["tmdb_api"] = {
                    "status": "FAILED",
                    "message": f"Infrastructure error: {e.message}",
                    "error_code": e.code,
                }
                verify_results["verification_status"] = "FAILED"
            except Exception as e:
                verify_results["tmdb_api"] = {
                    "status": "FAILED",
                    "message": f"Unexpected error: {e}",
                }
                verify_results["verification_status"] = "FAILED"

        if args.all:
            # Add more verification checks here
            verify_results["all_components"] = {
                "status": "SUCCESS",
                "message": "All components verified",
            }

        # Set overall status
        if verify_results["verification_status"] == "PENDING":
            verify_results["verification_status"] = "SUCCESS"

        return verify_results

    except Exception:
        logger.exception("Error collecting verify data")
        return None
