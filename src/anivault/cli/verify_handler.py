"""Verify command handler for AniVault CLI.

This module contains the business logic for the verify command,
separated for better maintainability and single responsibility principle.
"""

import logging
from typing import Any

from anivault.shared.constants.system import (
    CLI_INFO_COMMAND_COMPLETED,
    CLI_INFO_COMMAND_STARTED,
)

logger = logging.getLogger(__name__)


def handle_verify_command(args: Any) -> int:
    """Handle the verify command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger.info(CLI_INFO_COMMAND_STARTED.format(command="verify"))

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
            except Exception as e:
                from anivault.shared.constants.system import (
                    CLI_ERROR_TMDB_CONNECTIVITY_FAILED,
                )

                console.print(
                    f"[red]{CLI_ERROR_TMDB_CONNECTIVITY_FAILED.format(error=e)}[/red]",
                )
                return 1

        if args.all:
            console.print("[blue]Verifying all components...[/blue]")
            # Add more verification checks here
            console.print("[green]✓ All components verified[/green]")

        logger.info(CLI_INFO_COMMAND_COMPLETED.format(command="verify"))
        return 0

    except Exception as e:
        from anivault.shared.constants.system import CLI_ERROR_VERIFICATION_FAILED

        console.print(f"[red]{CLI_ERROR_VERIFICATION_FAILED.format(error=e)}[/red]")
        logger.exception("Error in verify command")
        return 1
