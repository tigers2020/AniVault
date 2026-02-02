"""Application context for GUI v2."""

from __future__ import annotations

import logging
from pathlib import Path

from anivault.config import Settings
from anivault.config.settings_provider import get_settings_provider
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
        self.settings: Settings = get_settings_provider().get_settings(config_path)
        # Use default config path if not provided
        self.config_path = Path(config_path) if config_path else Path("config/config.toml")
        logger.debug("GUI v2 AppContext initialized with config_path: %s", self.config_path)
