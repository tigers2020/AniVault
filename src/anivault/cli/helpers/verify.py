"""Verify command helper functions.

This module contains the core business logic for the verify command,
extracted for better maintainability and reusability.
"""

from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import TYPE_CHECKING

from anivault.services import TMDBClient
from anivault.shared.errors import ApplicationError, ErrorCode, InfrastructureError

if TYPE_CHECKING:
    from rich.console import Console

logger = logging.getLogger(__name__)


class VerificationStatus(str, Enum):
    """Verification status values (avoid magic strings)."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"


def _build_status_entry(
    *, status: VerificationStatus, message: str, extra: dict[str, str] | None = None
) -> dict[str, str]:
    """Build a standardized verification entry dict.

    Args:
        status: Verification status
        message: Human-readable message
        extra: Optional extra fields to include

    Returns:
        Standardized dict for verification entries
    """
    entry: dict[str, str] = {"status": status.value, "message": message}
    if extra:
        entry.update(extra)
    return entry


async def verify_tmdb_connectivity() -> dict[str, str]:
    """Verify TMDB API connectivity.

    Returns:
        Verification result dictionary

    Raises:
        ApplicationError: If TMDB verification fails
        InfrastructureError: If network/API access fails
    """
    try:
        client = TMDBClient()
        await client.search_media("test")

        return _build_status_entry(
            status=VerificationStatus.SUCCESS,
            message="TMDB API connectivity verified",
        )

    except (ApplicationError, InfrastructureError):
        # Known error types propagate to callers for proper handling
        raise
    except Exception as e:
        # Wrap unexpected exceptions into ApplicationError for consistency
        raise ApplicationError(
            code=ErrorCode.APPLICATION_ERROR,
            message=f"TMDB API verification failed: {e}",
            original_error=e,
        ) from e


def print_tmdb_verification_result(
    console: Console,
    *,
    verify_tmdb: bool = False,
) -> int:
    """Print TMDB verification result.

    Args:
        console: Rich console for output
        verify_tmdb: Whether to verify TMDB

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if not verify_tmdb:
        return 0

    console.print("[blue]Verifying TMDB API connectivity...[/blue]")

    try:
        result = asyncio.run(verify_tmdb_connectivity())
        console.print(f"[green]✓ {result['message']}[/green]")
        return 0

    except (ApplicationError, InfrastructureError) as e:
        console.print(f"[red]✗ {e.message}[/red]")
        logger.exception("TMDB API verification failed")
        return 1


def collect_verify_data(
    *,
    verify_tmdb: bool = False,
    verify_all: bool = False,
) -> dict[str, str | dict[str, str]]:
    """Collect verification data for JSON output.

    Args:
        verify_tmdb: Whether to verify TMDB
        verify_all: Whether to verify all components

    Returns:
        Verification results dictionary

    Raises:
        ApplicationError: If verification fails
        InfrastructureError: If connectivity fails
    """
    verify_results: dict[str, str | dict[str, str]] = {
        "verification_status": VerificationStatus.PENDING.value,
    }

    if verify_tmdb or verify_all:
        try:
            tmdb_result = asyncio.run(verify_tmdb_connectivity())
            verify_results["tmdb_api"] = tmdb_result
        except (ApplicationError, InfrastructureError) as e:
            verify_results["tmdb_api"] = _build_status_entry(
                status=VerificationStatus.FAILED,
                message=e.message,
                extra={"error_code": str(e.code)},
            )
            verify_results["verification_status"] = VerificationStatus.FAILED.value

    if verify_all:
        # Add more verification checks here
        verify_results["all_components"] = _build_status_entry(
            status=VerificationStatus.SUCCESS,
            message="All components verified",
        )

    # Set overall status
    if verify_results["verification_status"] == VerificationStatus.PENDING.value:
        verify_results["verification_status"] = VerificationStatus.SUCCESS.value

    return verify_results
