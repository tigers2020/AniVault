"""Settings command implementation."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import click
from rich.console import Console
from rich.table import Table

from anivault.core.logging import get_logger

logger = get_logger(__name__)
console = Console()


@click.command()
@click.option(
    "--show",
    is_flag=True,
    help="Show current settings",
)
@click.option(
    "--set",
    "set_key",
    help="Set a configuration key",
)
@click.option(
    "--value",
    help="Value for the configuration key",
)
@click.option(
    "--tmdb-key",
    help="Set TMDB API key",
)
@click.option(
    "--rate-limit",
    type=float,
    help="Set default rate limit (requests per second)",
)
@click.option(
    "--concurrency",
    type=int,
    help="Set default concurrency limit",
)
@click.option(
    "--language",
    help="Set default language",
)
@click.option(
    "--config-file",
    type=click.Path(path_type=Path),
    help="Configuration file path",
)
@click.pass_context
def settings(
    ctx: click.Context,
    show: bool,
    set_key: Optional[str],
    value: Optional[str],
    tmdb_key: Optional[str],
    rate_limit: Optional[float],
    concurrency: Optional[int],
    language: Optional[str],
    config_file: Optional[Path],
) -> None:
    """Manage AniVault settings.

    This command allows you to view and modify AniVault configuration
    settings including TMDB API key, rate limits, and other preferences.
    """
    json_output = ctx.obj.get("json_output", False)

    try:
        # Load current configuration
        config = _load_config(config_file)

        # Handle different operations
        if show:
            _show_settings(config, json_output)
        elif set_key and value:
            _set_setting(config, set_key, value, config_file, json_output)
        elif tmdb_key:
            _set_setting(config, "tmdb_api_key", tmdb_key, config_file, json_output)
        elif rate_limit is not None:
            _set_setting(config, "rate_limit", rate_limit, config_file, json_output)
        elif concurrency is not None:
            _set_setting(config, "concurrency", concurrency, config_file, json_output)
        elif language:
            _set_setting(config, "language", language, config_file, json_output)
        else:
            # Default: show settings
            _show_settings(config, json_output)

        sys.exit(0)

    except Exception as e:
        logger.exception("Settings operation failed")
        if json_output:
            _output_json_error("E-SETTINGS-FAIL", str(e))
        else:
            console.print(f"[red]Settings operation failed: {e}[/red]")
        sys.exit(1)


def _load_config(config_file: Optional[Path]) -> Dict[str, Any]:
    """Load configuration from file."""
    if config_file and config_file.exists():
        with open(config_file, encoding="utf-8") as f:
            return json.load(f)

    # Default configuration
    return {
        "tmdb_api_key": "",
        "rate_limit": 35.0,
        "concurrency": 4,
        "language": "en-US",
        "max_workers": 4,
        "naming_schema": "{title} ({year})/Season {season:02d}",
        "conflict_resolution": "rename",
    }


def _show_settings(config: Dict[str, Any], json_output: bool) -> None:
    """Show current settings."""
    if json_output:
        _output_json_event("settings", "show", config)
    else:
        console.print("[blue]Current Settings[/blue]")

        # Create table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        for key, value in config.items():
            # Mask sensitive values
            display_value = "***" if "key" in key.lower() else str(value)
            table.add_row(key, display_value)

        console.print(table)


def _set_setting(
    config: Dict[str, Any],
    key: str,
    value: Any,
    config_file: Optional[Path],
    json_output: bool,
) -> None:
    """Set a configuration value."""
    old_value = config.get(key)
    config[key] = value

    # Save configuration
    if config_file:
        _save_config(config, config_file)

    if json_output:
        _output_json_event(
            "settings",
            "set",
            {
                "key": key,
                "old_value": old_value,
                "new_value": value,
            },
        )
    else:
        console.print(f"[green]Setting '{key}' updated[/green]")
        console.print(f"  Old value: {old_value}")
        console.print(f"  New value: {value}")


def _save_config(config: Dict[str, Any], config_file: Path) -> None:
    """Save configuration to file."""
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


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
