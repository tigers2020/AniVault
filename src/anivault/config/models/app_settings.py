"""Application and logging configuration models.

This module contains configuration models for application-level
settings and logging configuration.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from anivault.shared.constants import Application, Logging


class AppSettings(BaseSettings):
    """Application configuration.

    This class manages application-level settings including
    name, version, debug mode, and theme.
    """

    model_config = {
        "env_prefix": "ANIVAULT_APP__",
        "env_nested_delimiter": "__",
        "env_ignore_empty": True,
        "extra": "ignore",
    }

    name: str = Field(default=Application.NAME, description="Application name")
    version: str = Field(default=Application.VERSION, description="Application version")
    description: str = Field(
        default="Anime Collection Management System",
        description="Application description",
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    theme: str = Field(default="light", description="Application theme (light, dark)")


class LoggingSettings(BaseModel):
    """Logging configuration.

    This class manages logging behavior including level, format,
    file output, and console output settings.
    """

    level: str = Field(default="INFO", description="Logging level")
    format_string: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
        alias="format",
    )
    file: str = Field(default=Logging.DEFAULT_FILE_PATH, description="Log file path")
    max_bytes: int = Field(
        default=Logging.MAX_BYTES,
        description="Maximum log file size in bytes",  # 10MB
    )
    backup_count: int = Field(
        default=Logging.BACKUP_COUNT,
        description="Number of backup log files to keep",
    )
    console_output: bool = Field(default=True, description="Enable console logging")


# Backward compatibility aliases
AppConfig = AppSettings
LoggingConfig = LoggingSettings


__all__ = [
    "AppConfig",  # Backward compatibility
    "AppSettings",
    "LoggingConfig",  # Backward compatibility
    "LoggingSettings",
]
