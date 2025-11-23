"""AniVault Settings Configuration Model.

Main Settings class that consolidates all configuration domains.
Moved to models package to avoid circular dependencies and improve structure.
"""

from __future__ import annotations

import logging
import typing
import warnings
from pathlib import Path
from typing import cast

import toml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Import domain models from refactored modules
from anivault.config.models.api_settings import (
    APISettings,
    TMDBSettings,
)
from anivault.config.models.app_settings import (
    AppSettings,
    LoggingSettings,
)
from anivault.config.models.cache_settings import CacheSettings
from anivault.config.models.folder_security_settings import (
    FolderSettings,
    SecuritySettings,
)
from anivault.config.models.grouping_settings import GroupingSettings
from anivault.config.models.performance_settings import (
    PerformanceSettings,
)
from anivault.config.models.scan_settings import (
    FilterSettings,
    ScanSettings,
)

logger = logging.getLogger(__name__)

# Type Safety Feature Flags
# Enable legacy dict/Any types for backward compatibility.
# Security Note: Setting this to True disables type safety guarantees and should
# ONLY be used during migration phases with appropriate safeguards.
# Default: False (type-safe mode)
USE_LEGACY_DICT_TYPES: typing.Final[bool] = False


class Settings(BaseSettings):
    """Lightweight settings facade providing unified configuration access.

    This facade consolidates all configuration domains (app, api, scan, etc.)
    with backward-compatible properties for deprecated field names.
    """

    model_config = SettingsConfigDict(
        env_prefix="ANIVAULT_",
        env_nested_delimiter="__",
        env_ignore_empty=True,
        extra="ignore",
    )

    # Primary configuration domains
    app: AppSettings = Field(default_factory=AppSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    api: APISettings = Field(default_factory=APISettings)
    scan: ScanSettings = Field(default_factory=ScanSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    performance: PerformanceSettings = Field(default_factory=PerformanceSettings)
    grouping: GroupingSettings = Field(default_factory=GroupingSettings)
    folders: FolderSettings | None = Field(default=None)
    security: SecuritySettings | None = Field(default=None)

    # Backward-compatible properties (deprecated)
    @property
    def tmdb(self) -> TMDBSettings:
        """DEPRECATED: Use settings.api.tmdb instead.

        This property provides backward compatibility but will be removed
        in a future version.
        """
        warnings.warn(
            "settings.tmdb is deprecated, use settings.api.tmdb instead",
            DeprecationWarning,
            stacklevel=2,
        )
        # Type checker workaround: Pydantic Field inference issue
        # Runtime: self.api is APISettings instance, not FieldInfo
        api = cast("APISettings", object.__getattribute__(self, "api"))
        return api.tmdb

    @property
    def file_processing(self) -> ScanSettings:
        """DEPRECATED: Use settings.scan instead.

        This property provides backward compatibility but will be removed
        in a future version.
        """
        warnings.warn(
            "settings.file_processing is deprecated, use settings.scan instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.scan

    @property
    def filter(self) -> FilterSettings:
        """DEPRECATED: Use settings.scan.filter_config instead.

        This property provides backward compatibility but will be removed
        in a future version.
        """
        warnings.warn(
            "settings.filter is deprecated, use settings.scan.filter_config instead",
            DeprecationWarning,
            stacklevel=2,
        )
        # Type checker workaround: Pydantic Field inference issue
        # Runtime: self.scan is ScanSettings instance, not FieldInfo
        scan = cast("ScanSettings", object.__getattribute__(self, "scan"))
        return scan.filter_config

    @classmethod
    def from_toml_file(cls, file_path: str | Path) -> Settings:
        """Load settings from TOML file with environment variable overrides."""

        file_path = Path(file_path)
        if not file_path.exists():
            msg = f"Configuration file not found: {file_path}"
            raise FileNotFoundError(msg)

        raw_config = toml.load(file_path)
        return cls(**raw_config)

    def to_toml_file(self, file_path: str | Path) -> None:
        """Save settings to TOML file.

        Security design:
        - API keys ARE saved to config file (required for functionality)
        - Logs mask API keys via __repr__ (security)
        - File permissions provide OS-level protection

        Note: Config files are not logs. They require API keys to function.
        """

        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize all config including API keys
        config_dict = self.model_dump(exclude_none=True, exclude_unset=False)

        with open(file_path, "w", encoding="utf-8") as f:
            toml.dump(config_dict, f)
