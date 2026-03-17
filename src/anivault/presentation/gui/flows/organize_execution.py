"""Organize execute flow: plan build, dialog, and execution.

Phase R2: Orchestration and plan/execute go through OrganizeUseCase only.
Phase 4: Dialog receives OrganizePlanItem list; raw plan kept for execute_plan only.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from PySide6.QtWidgets import QDialog

from anivault.application.dtos.organize import file_operation_to_dto
from anivault.application.use_cases.organize_use_case import OrganizeUseCase
from anivault.config.settings_provider import get_settings_provider
from anivault.presentation.gui.builders.organize_builder import OrganizeBuilder
from anivault.presentation.gui.dialogs.organize_dry_run_dialog import OrganizeDryRunDialog

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from anivault.presentation.gui.main_window import MainWindow


def run_organize_execute_flow(
    window: MainWindow,
    on_refresh_after_organize: Callable[[], None],
) -> None:
    """Run the full organize execute flow: source files, plan, dialog, execute.

    Uses window for status_bar, app_context, get_current_scan_results,
    is_subtitles_view. Calls on_refresh_after_organize after successful execution.
    """
    if not window.organize_controller:
        window.status_bar.set_status("정리 컨트롤러가 초기화되지 않았습니다.", "error")
        return

    files = _get_organize_source_files(window)
    if not files:
        return

    _load_organize_settings(window)
    directory = _resolve_organize_directory(window)
    if directory is None:
        window.status_bar.set_status("정리 경로를 확인할 수 없습니다.", "error")
        return

    destination = _get_organize_destination(window) or "Anime"
    options = OrganizeBuilder.build_organize_options(
        directory,
        destination=destination,
        dry_run=True,
        use_subtitles=window.is_subtitles_view(),
    )

    use_case = window.app_context.container.organize_use_case()
    if getattr(options, "enhanced", False):
        plan = use_case.generate_enhanced_plan_from_metadata(files, destination=getattr(options, "destination", "Anime"))
    else:
        plan = use_case.generate_plan_from_metadata(files, settings=window.app_context.settings)

    if not plan:
        window.status_bar.set_status("정리 계획이 비어 있습니다.", "warn")
        return

    plan_dtos = [file_operation_to_dto(op) for op in plan]
    if not _confirm_organize_via_dialog(window, plan_dtos):
        window.status_bar.set_status("파일 정리가 취소되었습니다.", "ok")
        return

    _execute_organize_plan(window, plan, options, on_refresh_after_organize, use_case)


def _get_organize_source_files(window: MainWindow) -> list | None:
    """Return current view's file list for organize, or None after setting status."""
    files = window.get_current_scan_results()
    if not files:
        window.status_bar.set_status("먼저 매칭을 완료하세요.", "warn")
        return None
    return files


def _load_organize_settings(window: MainWindow) -> None:
    """Load app settings and log folder config."""
    config_file = window.app_context.config_path
    logger.info("Loading settings from: %s", config_file)
    window.app_context.settings = get_settings_provider().get_settings(config_file)
    folders = window.app_context.settings.folders
    if folders:
        logger.info(
            "Organize settings loaded: template=%s, target_folder=%s",
            folders.organize_path_template,
            folders.target_folder,
        )
    else:
        logger.error("Folder settings not found in configuration - organizing will use defaults!")


def _get_organize_destination(window: MainWindow) -> str:
    """Return target folder from settings or empty string."""
    folders = window.app_context.settings.folders
    return (folders.target_folder or "") if folders else ""


def _confirm_organize_via_dialog(window: MainWindow, plan: list) -> bool:
    """Show dry-run dialog and return True if user accepted and confirmed."""
    preview = OrganizeDryRunDialog(plan, window)
    return preview.exec() == QDialog.DialogCode.Accepted and preview.is_confirmed()


def _execute_organize_plan(
    window: MainWindow,
    plan: list,
    options: object,
    on_refresh_after_organize: Callable[[], None],
    use_case: OrganizeUseCase,
) -> None:
    """Run organization plan via UseCase and refresh UI via callback."""
    window.status_bar.set_status("파일 정리 실행 중...", "ok")
    directory = getattr(options, "directory", options)
    source_directory = directory.path if hasattr(directory, "path") else Path(str(directory))
    try:
        use_case.execute_plan(
            plan,
            source_directory,
            settings=window.app_context.settings,
        )
        window.status_bar.set_status("정리 완료", "ok")
        on_refresh_after_organize()
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.exception("Organize execution failed")
        window.status_bar.set_status(str(exc) or "정리 실행 실패", "error")


def _resolve_organize_directory(window: MainWindow) -> Path | None:
    """Resolve the organize directory from settings or scan results."""
    if window.app_context.settings.folders and window.app_context.settings.folders.source_folder:
        source_path = Path(window.app_context.settings.folders.source_folder)
        if source_path.exists() and source_path.is_dir():
            return source_path

    results = window.get_current_scan_results()
    if results:
        candidate = Path(results[0].file_path).parent
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None
