"""Status command implementation."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import click
from rich.console import Console
from rich.table import Table

from anivault.core.logging import get_logger

logger = get_logger(__name__)
console = Console()


@click.command()
@click.option(
    "--diag",
    is_flag=True,
    help="Show diagnostic information",
)
@click.option(
    "--last-run",
    is_flag=True,
    help="Show last run information",
)
@click.option(
    "--metrics",
    is_flag=True,
    help="Show performance metrics",
)
@click.pass_context
def status(
    ctx: click.Context,
    diag: bool,
    last_run: bool,
    metrics: bool,
) -> None:
    """Show AniVault status and diagnostic information.

    This command provides status information about the last run,
    system diagnostics, and performance metrics.
    """
    json_output = ctx.obj.get("json_output", False)

    try:
        if diag:
            _show_diagnostics(json_output)
        elif last_run:
            _show_last_run(json_output)
        elif metrics:
            _show_metrics(json_output)
        else:
            # Default: show general status
            _show_general_status(json_output)

        sys.exit(0)

    except Exception as e:
        logger.exception("Status command failed")
        if json_output:
            _output_json_error("E-STATUS-FAIL", str(e))
        else:
            console.print(f"[red]Status command failed: {e}[/red]")
        sys.exit(1)


def _show_general_status(json_output: bool) -> None:
    """Show general status information."""
    status_info = _get_general_status()

    if json_output:
        _output_json_event("status", "general", status_info)
    else:
        console.print("[blue]AniVault Status[/blue]")

        # Create table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")

        table.add_row("CLI", status_info["cli_status"])
        table.add_row("TMDB API", status_info["tmdb_status"])
        table.add_row("Cache", status_info["cache_status"])
        table.add_row("Logging", status_info["logging_status"])
        table.add_row("Last Run", status_info["last_run"])

        console.print(table)


def _get_general_status() -> Dict[str, Any]:
    """Get general status information."""
    return {
        "cli_status": "Ready",
        "tmdb_status": "Not configured",
        "cache_status": "Available",
        "logging_status": "Active",
        "last_run": "Never",
    }


def _show_diagnostics(json_output: bool) -> None:
    """Show diagnostic information."""
    diag_info = _get_diagnostics()

    if json_output:
        _output_json_event("status", "diagnostics", diag_info)
    else:
        console.print("[blue]System Diagnostics[/blue]")

        # Create table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Component", style="cyan")
        table.add_column("Value", style="green")

        for key, value in diag_info.items():
            table.add_row(key, str(value))

        console.print(table)


def _get_diagnostics() -> Dict[str, Any]:
    """Get diagnostic information."""
    import os
    import platform
    import sys

    return {
        "platform": platform.platform(),
        "python_version": sys.version,
        "anivault_version": "3.0.0",
        "working_directory": str(Path.cwd()),
        "user_home": str(Path.home()),
        "long_path_support": _check_long_path_support(),
        "cache_directory": str(Path(".anivault/cache")),
        "logs_directory": str(Path("logs")),
        "tmdb_api_key_set": bool(os.getenv("TMDB_API_KEY")),
        "max_path_length": _get_max_path_length(),
    }


def _check_long_path_support() -> bool:
    """Check if long path support is available."""
    try:
        # Try to create a long path
        test_path = Path("x" * 300)
        test_path.mkdir(exist_ok=True)
        test_path.rmdir()
        return True
    except (OSError, FileNotFoundError):
        return False


def _get_max_path_length() -> int:
    """Get maximum path length."""
    import platform

    if platform.system() == "Windows":
        return 260  # Default Windows limit
    return 4096  # Typical Unix limit


def _show_last_run(json_output: bool) -> None:
    """Show last run information."""
    last_run_info = _get_last_run_info()

    if json_output:
        _output_json_event("status", "last_run", last_run_info)
    else:
        console.print("[blue]Last Run Information[/blue]")

        # Create table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        for key, value in last_run_info.items():
            table.add_row(key, str(value))

        console.print(table)


def _get_last_run_info() -> Dict[str, Any]:
    """Get last run information."""
    # This would read from actual run logs
    return {
        "timestamp": "Never",
        "source_directory": "N/A",
        "destination_directory": "N/A",
        "files_processed": 0,
        "files_matched": 0,
        "files_organized": 0,
        "errors": 0,
        "duration": "N/A",
    }


def _show_metrics(json_output: bool) -> None:
    """Show performance metrics."""
    metrics_info = _get_metrics()

    if json_output:
        _output_json_event("status", "metrics", metrics_info)
    else:
        console.print("[blue]Performance Metrics[/blue]")

        # Create table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        for key, value in metrics_info.items():
            table.add_row(key, str(value))

        console.print(table)


def _get_metrics() -> Dict[str, Any]:
    """Get performance metrics."""
    # This would read from actual performance logs
    return {
        "scan_speed": "N/A",
        "match_speed": "N/A",
        "organize_speed": "N/A",
        "cache_hit_rate": "N/A",
        "memory_usage": "N/A",
        "cpu_usage": "N/A",
    }


def _output_json_event(phase: str, event: str, fields: Dict[str, Any]) -> None:
    """Output event in JSON format."""
    event_data = {
        "phase": phase,
        "event": event,
        "ts": datetime.utcnow().isoformat() + "Z",
        "fields": fields,
    }
    print(json.dumps(event_data))


def _output_json_error(error_code: str, message: str) -> None:
    """Output error in JSON format."""
    error_data = {
        "phase": "error",
        "event": "error",
        "ts": datetime.utcnow().isoformat() + "Z",
        "fields": {
            "error_code": error_code,
            "message": message,
            "level": "ERROR",
        },
    }
    print(json.dumps(error_data))
