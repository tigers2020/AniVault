"""Application context for GUI v2."""

from __future__ import annotations

import logging
from pathlib import Path

from anivault.config import Settings, load_settings
from anivault.containers import Container

logger = logging.getLogger(__name__)


class AppContext:
    """Shared application context for GUI v2."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        """Initialize the application context.

        Args:
            config_path: Optional path to configuration file.
        """
        self.container = Container()
        self.settings: Settings = load_settings(config_path)
        # Use default config path if not provided
        self.config_path = Path(config_path) if config_path else Path("config/config.toml")
        logger.debug("GUI v2 AppContext initialized with config_path: %s", self.config_path)
