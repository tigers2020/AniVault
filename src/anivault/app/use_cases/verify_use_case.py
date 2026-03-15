"""Verify use case (Phase R4B).

Moves TMDB connectivity verification from the CLI helper layer into the
app layer.  The CLI verify_handler calls this use case and passes the
resulting dict to the helper (formatter/presenter) for output rendering.
"""

from __future__ import annotations

import logging
from enum import Enum

from anivault.services import TMDBClient
from anivault.shared.errors import ApplicationError, ErrorCode, InfrastructureError

logger = logging.getLogger(__name__)


class VerificationStatus(str, Enum):
    """Standard verification result statuses."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"


def _build_status_entry(
    *,
    status: VerificationStatus,
    message: str,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build a standardised verification result dict."""
    entry: dict[str, str] = {"status": status.value, "message": message}
    if extra:
        entry.update(extra)
    return entry


class VerifyUseCase:
    """Verify system component connectivity.

    Responsibilities:
    - TMDB API connectivity check (moved from cli/helpers/verify.py).
    - --all placeholder success (R4B: outward behavior preserved;
      real multi-component checks deferred to a future phase).
    """

    def __init__(self, tmdb_client: TMDBClient) -> None:
        self._tmdb_client = tmdb_client

    async def verify_tmdb(self) -> dict[str, str]:
        """Verify TMDB API connectivity.

        Returns:
            Status dict with "status" and "message" keys.

        Raises:
            ApplicationError: On unexpected errors.
            InfrastructureError: On network / API access failures.
        """
        try:
            await self._tmdb_client.search_media("test")
            return _build_status_entry(
                status=VerificationStatus.SUCCESS,
                message="TMDB API connectivity verified",
            )
        except (ApplicationError, InfrastructureError):
            raise
        except Exception as exc:
            raise ApplicationError(
                code=ErrorCode.APPLICATION_ERROR,
                message=f"TMDB API verification failed: {exc}",
                original_error=exc,
            ) from exc

    async def verify_all(self) -> dict[str, dict[str, str]]:
        """Verify all components.

        R4B: TMDB result is real; all_components is a placeholder that
        preserves the existing outward behavior.  Additional component
        checks will be wired in a future phase.

        Returns:
            Dict mapping component names to their status dicts.
        """
        results: dict[str, dict[str, str]] = {}

        try:
            results["tmdb_api"] = await self.verify_tmdb()
        except (ApplicationError, InfrastructureError) as exc:
            results["tmdb_api"] = _build_status_entry(
                status=VerificationStatus.FAILED,
                message=exc.message,
                extra={"error_code": str(exc.code)},
            )

        # Placeholder: preserved from the original outward behavior.
        results["all_components"] = _build_status_entry(
            status=VerificationStatus.SUCCESS,
            message="All components verified",
        )

        return results
