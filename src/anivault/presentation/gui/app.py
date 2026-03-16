"""AniVault GUI v2 Application Entry Point."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from anivault.presentation.gui.app_context import AppContext
from anivault.presentation.gui.main_window import MainWindow
from anivault.presentation.gui.styles.styles import StyleManager
from anivault.shared.constants.logging import LogConfig
from anivault.shared.constants.system import FileSystem
from anivault.shared.constants.validation_constants import PIPELINE_CACHE_DB
from anivault.shared.logging import configure_logging
from anivault.utils.resource_path import get_project_root

logger = logging.getLogger(__name__)


def _log_startup_paths() -> None:
    """Log cwd, project root, and parser cache DB path once at GUI startup for diagnostics."""
    cwd = Path.cwd().resolve()
    try:
        project_root = get_project_root().resolve()
    except Exception as e:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        logger.warning("get_project_root() failed: %s", e)
        project_root = cwd
    parser_cache_db = project_root / FileSystem.CACHE_DIRECTORY / PIPELINE_CACHE_DB
    logger.info(
        "GUI startup paths: cwd=%s, project_root=%s, parser_cache_db=%s",
        cwd,
        project_root,
        parser_cache_db,
    )
    # R5: use find_spec so gui_v2.app does not directly import from anivault.core
    try:
        import importlib.util

        _p_spec = importlib.util.find_spec("anivault.core.pipeline.components.parser")
        _o_spec = importlib.util.find_spec("anivault.core.pipeline.domain.orchestrator")
        logger.info(
            "Pipeline module paths: parser=%s, orchestrator=%s",
            _p_spec.origin if _p_spec else "N/A",
            _o_spec.origin if _o_spec else "N/A",
        )
    except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught
        logger.warning("Could not log pipeline module paths: %s", e)


class AniVaultGUIv2:
    """Main GUI v2 application class."""

    def __init__(self) -> None:
        """Initialize GUI v2 application."""
        self.app: QApplication | None = None
        self.main_window: MainWindow | None = None
        self.style_manager: StyleManager | None = None
        self.app_context: AppContext | None = None

    def initialize(self) -> bool:
        """
        Initialize the GUI v2 application.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Create QApplication
            self.app = QApplication(sys.argv)
            self.app.setApplicationName("AniVault")
            self.app.setApplicationVersion("2.0.0")
            self.app.setOrganizationName("AniVault")

            # Initialize shared application context
            self.app_context = AppContext()

            # Initialize style manager with dark theme
            self.style_manager = StyleManager(theme=StyleManager.DARK_THEME)

            # Create main window
            self.main_window = MainWindow(app_context=self.app_context)

            # Apply styles
            if self.style_manager:
                self.style_manager.apply_styles(self.app)

            logger.info("GUI v2 application initialized successfully")
            return True

        except Exception:
            logger.exception("Failed to initialize GUI v2")
            return False

    def run(self) -> int:
        """
        Run the GUI application.

        Returns:
            Application exit code
        """
        if not self.app or not self.main_window:
            logger.error("Application not initialized. Call initialize() first.")
            return 1

        self.main_window.show()
        return self.app.exec()


def main() -> int:
    """Main entry point for GUI v2."""
    configure_logging(
        level=logging.INFO,
        log_dir=LogConfig.DEFAULT_LOG_DIR,
        log_file=LogConfig.DEFAULT_FILE,
        use_rich=True,
        use_json_console=False,
        enable_file=True,
        enable_console=True,
    )

    _log_startup_paths()

    app = AniVaultGUIv2()
    if not app.initialize():
        return 1

    return app.run()


if __name__ == "__main__":
    sys.exit(main())
