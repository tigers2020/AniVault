"""Verify use case (Phase R4B).

Moves TMDB connectivity verification from the CLI helper layer into the
app layer.  The CLI verify_handler calls this use case and passes the
resulting dict to the helper (formatter/presenter) for output rendering.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from enum import Enum
from pathlib import Path
from typing import NotRequired, Protocol, TypedDict

from anivault.config.loader import load_settings
from anivault.services import TMDBClient
from anivault.shared.constants.system import FileSystem
from anivault.shared.constants.validation_constants import TMDB_CACHE_DB
from anivault.shared.errors import ApplicationError, ErrorCode, InfrastructureError
from anivault.utils.resource_path import get_project_root

logger = logging.getLogger(__name__)


class VerificationStatus(str, Enum):
    """Standard verification result statuses."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"


class VerificationEntry(TypedDict):
    """Verification result entry for a single component."""

    status: str
    message: str
    error_code: NotRequired[str]
    path: NotRequired[str]


class ComponentVerifier(Protocol):
    """Protocol for pluggable component verifiers."""

    @property
    def name(self) -> str:
        """Component key name in verify_all output."""

    def verify(self) -> VerificationEntry:
        """Return a verification entry for this component."""


class SettingsVerifier:
    """Verify runtime settings availability and required TMDB key."""

    @property
    def name(self) -> str:
        return "settings"

    def verify(self) -> VerificationEntry:
        try:
            settings = load_settings()
            api_key = settings.api.tmdb.api_key.strip()
            if not api_key:
                return _build_status_entry(
                    status=VerificationStatus.FAILED,
                    message="Settings loaded but TMDB API key is missing",
                )
            return _build_status_entry(
                status=VerificationStatus.SUCCESS,
                message="Settings loaded successfully",
            )
        except Exception as exc:  # noqa: BLE001
            return _build_status_entry(
                status=VerificationStatus.FAILED,
                message=f"Settings verification failed: {exc}",
            )


class CacheVerifier:
    """Verify TMDB cache database readability."""

    def __init__(self, cache_db_path: Path | None = None) -> None:
        self._cache_db_path = cache_db_path or (
            get_project_root() / FileSystem.CACHE_DIRECTORY / TMDB_CACHE_DB
        )

    @property
    def name(self) -> str:
        return "cache"

    def verify(self) -> VerificationEntry:
        if not self._cache_db_path.exists():
            return _build_status_entry(
                status=VerificationStatus.FAILED,
                message="TMDB cache database not found",
                extra={"path": str(self._cache_db_path)},
            )
        try:
            with self._cache_db_path.open("rb") as cache_file:
                cache_file.read(1)
            return _build_status_entry(
                status=VerificationStatus.SUCCESS,
                message="TMDB cache database is readable",
                extra={"path": str(self._cache_db_path)},
            )
        except PermissionError:
            return _build_status_entry(
                status=VerificationStatus.FAILED,
                message="TMDB cache database permission denied",
                extra={"path": str(self._cache_db_path)},
            )
        except OSError as exc:
            return _build_status_entry(
                status=VerificationStatus.FAILED,
                message=f"TMDB cache database verification failed: {exc}",
                extra={"path": str(self._cache_db_path)},
            )


def _build_status_entry(
    *,
    status: VerificationStatus,
    message: str,
    extra: dict[str, str] | None = None,
) -> VerificationEntry:
    """Build a standardised verification result dict."""
    entry: VerificationEntry = {"status": status.value, "message": message}
    if extra:
        entry.update(extra)
    return entry


class VerifyUseCase:
    """Verify system component connectivity.

    Responsibilities:
    - TMDB API connectivity check (moved from cli/helpers/verify.py).
    - Multi-component verification via pluggable ComponentVerifier protocol.
      Each verifier contributes a named entry; all_components aggregates the result.
    """

    def __init__(
        self,
        tmdb_client: TMDBClient,
        component_verifiers: Sequence[ComponentVerifier] | None = None,
    ) -> None:
        self._tmdb_client = tmdb_client
        self._component_verifiers: Sequence[ComponentVerifier] = (
            tuple(component_verifiers)
            if component_verifiers is not None
            else (SettingsVerifier(), CacheVerifier())
        )

    async def verify_tmdb(self) -> VerificationEntry:
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

    async def verify_all(self) -> dict[str, VerificationEntry]:
        """Verify all components.

        Safe Option:
        - Returns component map only (no top-level verification_status key).
        - all_components is computed from real component statuses.
        - Top-level verification_status remains the helper responsibility.

        Returns:
            Dict mapping component names to their status dicts.
        """
        results: dict[str, VerificationEntry] = {}

        try:
            results["tmdb_api"] = await self.verify_tmdb()
        except (ApplicationError, InfrastructureError) as exc:
            results["tmdb_api"] = _build_status_entry(
                status=VerificationStatus.FAILED,
                message=exc.message,
                extra={"error_code": str(exc.code)},
            )

        for verifier in self._component_verifiers:
            try:
                results[verifier.name] = verifier.verify()
            except Exception as exc:  # noqa: BLE001
                results[verifier.name] = _build_status_entry(
                    status=VerificationStatus.FAILED,
                    message=f"{verifier.name} verification failed: {exc}",
                )

        any_failed = any(
            entry.get("status") == VerificationStatus.FAILED.value for entry in results.values()
        )
        results["all_components"] = _build_status_entry(
            status=VerificationStatus.FAILED if any_failed else VerificationStatus.SUCCESS,
            message="Some components failed" if any_failed else "All components verified",
        )

        return results
