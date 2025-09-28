"""Main CLI entry point for AniVault."""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from anivault.core.config import load_config
from anivault.core.logging import get_logger

# Initialize console and logger
console = Console()
logger = get_logger(__name__)


@click.group()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    default="INFO",
    help="Set logging level",
)
@click.option(
    "--json",
    is_flag=True,
    help="Output in JSON format (NDJSON)",
)
@click.option(
    "--no-color",
    is_flag=True,
    help="Disable colored output",
)
@click.pass_context
def cli(
    ctx: click.Context,
    config: Optional[Path],
    log_level: str,
    json: bool,
    no_color: bool,
) -> None:
    """AniVault v3 CLI - Anime file organization tool.

    A powerful command-line tool for organizing anime files using TMDB API
    for metadata matching and intelligent file organization.
    """

    # Store global options in context
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["log_level"] = log_level
    ctx.obj["json_output"] = json
    ctx.obj["no_color"] = no_color

    # Load configuration
    try:
        app_config = load_config(config)
        ctx.obj["config"] = app_config
        logger.info("Configuration loaded successfully")
    except Exception as e:
        logger.error("Failed to load configuration: %s", e)
        if json:
            _output_json_error("E-CONFIG-LOAD", str(e))
        else:
            console.print(f"[red]Error: Failed to load configuration: {e}[/red]")
        sys.exit(2)


def _show_version() -> None:
    """Show version information."""
    import platform
    import sys

    import anivault

    version_info = {
        "app_version": anivault.__version__,
        "python_version": sys.version,
        "platform": platform.platform(),
        "build_date": "2025-01-27T00:00:00Z",  # Will be replaced by build process
        "git_commit": "unknown",  # Will be replaced by build process
        "pyinstaller_version": "unknown",  # Will be replaced by build process
    }

    console.print(f"AniVault CLI v{version_info['app_version']}")
    console.print(f"Python: {version_info['python_version']}")
    console.print(f"Platform: {version_info['platform']}")
    console.print(f"Build Date: {version_info['build_date']}")
    console.print(f"Git Commit: {version_info['git_commit']}")
    console.print(f"PyInstaller: {version_info['pyinstaller_version']}")


def _output_json_error(error_code: str, message: str) -> None:
    """Output error in JSON format."""
    import json
    from datetime import datetime

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


# Import and register command groups
from anivault.cli.commands import cache, match, organize, run, scan, settings, status


# Add version command
@cli.command()
def version() -> None:
    """Show version information."""
    _show_version()


# Register command groups
cli.add_command(run.run)
cli.add_command(scan.scan)
cli.add_command(match.match)
cli.add_command(organize.organize)
cli.add_command(cache.cache)
cli.add_command(settings.settings)
cli.add_command(status.status)


if __name__ == "__main__":
    cli()
