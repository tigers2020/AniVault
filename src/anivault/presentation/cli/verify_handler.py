"""Verify command handler for AniVault CLI.

Orchestration entry point: Container → VerifyUseCase → helper (format only).
This handler calls VerifyUseCase for all verification logic; the helper
module (cli/helpers/verify.py) is a pure presenter/formatter.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any

import typer
from dependency_injector.wiring import Provide, inject
from rich.console import Console

from anivault.application.use_cases.verify_use_case import VerifyUseCase
from anivault.presentation.cli.common.context import get_cli_context
from anivault.presentation.cli.common.error_decorator import handle_cli_errors
from anivault.presentation.cli.common.setup_decorator import setup_handler
from anivault.presentation.cli.helpers.verify import (
    format_verify_result_for_json,
    print_all_components_result,
    print_tmdb_verification_result,
)
from anivault.presentation.cli.json_formatter import format_json_output
from anivault.infrastructure.composition import Container
from anivault.shared.constants import CLI, CLIDefaults
from anivault.shared.errors import ApplicationError, InfrastructureError
from anivault.shared.types.cli import VerifyOptions

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


@inject
async def _run_verify(
    options: VerifyOptions,
    *,
    use_case: VerifyUseCase = Provide[Container.verify_use_case],
) -> dict[str, Any]:
    """Execute the appropriate verification via VerifyUseCase.

    Returns a normalised dict for the helper/formatter.
    Keys produced:
      - tmdb_result: dict | None
      - all_components_result: dict | None
      - error: str | None
    """
    if options.all_components:
        result = await use_case.verify_all()
        return {"tmdb_result": None, "all_components_result": result, "error": None}

    if options.tmdb:
        result = await use_case.verify_tmdb()
        return {"tmdb_result": result, "all_components_result": None, "error": None}

    # Nothing selected; treat as a no-op success.
    return {"tmdb_result": None, "all_components_result": None, "error": None}


# ---------------------------------------------------------------------------
# Command entry point
# ---------------------------------------------------------------------------


@setup_handler(supports_json=True)
@handle_cli_errors(operation="handle_verify", command_name="verify")
def handle_verify_command(options: VerifyOptions, **kwargs: Any) -> int:
    """Handle the verify command.

    Args:
        options: Validated verify command options.
        **kwargs: Injected by decorators (console, logger_adapter).

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    console: Console = kwargs.get("console") or Console()
    logger_adapter = kwargs.get("logger_adapter", logger)

    logger_adapter.info(CLI.INFO_COMMAND_STARTED.format(command="verify"))

    context = get_cli_context()
    is_json_output = bool(context and context.is_json_output_enabled())

    # Execute verification in app layer; single asyncio.run boundary here.
    try:
        verify_payload = asyncio.run(_run_verify(options))
    except (ApplicationError, InfrastructureError) as exc:
        error_msg = exc.message
        if is_json_output:
            json_output = format_json_output(
                success=False,
                command="verify",
                errors=[error_msg],
            )
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            console.print(f"[red]✗ {error_msg}[/red]")
            logger_adapter.exception("Verification failed")
        return CLIDefaults.EXIT_ERROR

    tmdb_result = verify_payload.get("tmdb_result")
    all_components_result = verify_payload.get("all_components_result")

    if is_json_output:
        return _emit_json_output(tmdb_result, all_components_result, logger_adapter)

    _emit_console_output(console, options, tmdb_result, all_components_result)
    logger_adapter.info(CLI.INFO_COMMAND_COMPLETED.format(command="verify"))
    return CLIDefaults.EXIT_SUCCESS


def _emit_json_output(
    tmdb_result: dict[str, str] | None,
    all_components_result: dict[str, dict[str, str]] | None,
    logger_adapter: Any,
) -> int:
    """Write JSON verification output and return exit code."""
    verify_data = format_verify_result_for_json(
        tmdb_result=tmdb_result,
        all_components_result=all_components_result,
    )
    json_output = format_json_output(
        success=True,
        command="verify",
        data=verify_data,
    )
    sys.stdout.buffer.write(json_output)
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()
    logger_adapter.info(CLI.INFO_COMMAND_COMPLETED.format(command="verify"))
    return CLIDefaults.EXIT_SUCCESS


def _emit_console_output(
    console: Console,
    options: VerifyOptions,
    tmdb_result: dict[str, str] | None,
    all_components_result: dict[str, dict[str, str]] | None,
) -> None:
    """Render verification results to console (result-only presenter calls)."""
    if options.all_components:
        # --all: TMDB + per-component verifiers aggregated into all_components entry
        console.print("[blue]Verifying all components...[/blue]")
        if all_components_result:
            if "tmdb_api" in all_components_result:
                print_tmdb_verification_result(console, all_components_result["tmdb_api"])
            if "all_components" in all_components_result:
                print_all_components_result(console, all_components_result["all_components"])
    elif options.tmdb and tmdb_result:
        console.print("[blue]Verifying TMDB API connectivity...[/blue]")
        print_tmdb_verification_result(console, tmdb_result)


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
    """Verify system components and connectivity.

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
        options = VerifyOptions(tmdb=tmdb, all=all_components)

        exit_code = handle_verify_command(options)

        if exit_code != CLIDefaults.EXIT_SUCCESS:
            raise typer.Exit(exit_code)

    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(CLIDefaults.EXIT_ERROR) from e
