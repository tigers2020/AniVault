"""Verify command helper functions — output/formatting only.

This module is a pure presenter/formatter.  It does NOT:
- import or instantiate TMDBClient
- import or call VerifyUseCase / Container / any app-layer use case
- perform any network I/O

All verification logic lives in VerifyUseCase (app/use_cases/verify_use_case.py).
The verify_handler is responsible for calling the use case and passing results here.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

logger = logging.getLogger(__name__)


class VerificationStatus(str, Enum):
    """Verification status values."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"


def _build_status_entry(
    *,
    status: VerificationStatus,
    message: str,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build a standardised verification entry dict.

    Args:
        status:  Verification status.
        message: Human-readable message.
        extra:   Optional extra fields to merge in.

    Returns:
        Standardised dict for verification entries.
    """
    entry: dict[str, str] = {"status": status.value, "message": message}
    if extra:
        entry.update(extra)
    return entry


# ---------------------------------------------------------------------------
# Console presenters
# ---------------------------------------------------------------------------


def print_tmdb_verification_result(console: Console, result: dict[str, str]) -> None:
    """Render a TMDB verification result to the console.

    Args:
        console: Rich console for output.
        result:  Dict with at minimum "status" and "message" keys, as
                 returned by VerifyUseCase.verify_tmdb().
    """
    status = result.get("status", VerificationStatus.FAILED.value)
    message = result.get("message", "Verification result unavailable")

    if status == VerificationStatus.SUCCESS.value:
        console.print(f"[green]✓ {message}[/green]")
    else:
        console.print(f"[red]✗ {message}[/red]")


def print_all_components_result(console: Console, result: dict[str, str]) -> None:
    """Render an all-components verification result to the console.

    Args:
        console: Rich console for output.
        result:  Dict with "status" and "message" keys.
    """
    status = result.get("status", VerificationStatus.FAILED.value)
    message = result.get("message", "Verification result unavailable")

    if status == VerificationStatus.SUCCESS.value:
        console.print(f"[green]✓ {message}[/green]")
    else:
        console.print(f"[red]✗ {message}[/red]")


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------


def format_verify_result_for_json(
    tmdb_result: dict[str, str] | None = None,
    all_components_result: dict[str, dict[str, str]] | None = None,
) -> dict[str, str | dict[str, str]]:
    """Build a JSON-serialisable verification result dict.

    Args:
        tmdb_result:           Result from VerifyUseCase.verify_tmdb() or None.
        all_components_result: Result from VerifyUseCase.verify_all() or None.

    Returns:
        Dict ready to pass to format_json_output(data=...).
    """
    verify_results: dict[str, str | dict[str, str]] = {
        "verification_status": VerificationStatus.PENDING.value,
    }

    if all_components_result is not None:
        # verify_all() returns the full component map; merge it in.
        verify_results.update(all_components_result)
        # Determine overall status from the individual results.
        any_failed = any(v.get("status") == VerificationStatus.FAILED.value for v in all_components_result.values() if isinstance(v, dict))
        verify_results["verification_status"] = VerificationStatus.FAILED.value if any_failed else VerificationStatus.SUCCESS.value
    elif tmdb_result is not None:
        verify_results["tmdb_api"] = tmdb_result
        verify_results["verification_status"] = tmdb_result.get("status", VerificationStatus.FAILED.value)
    else:
        verify_results["verification_status"] = VerificationStatus.SUCCESS.value

    return verify_results
