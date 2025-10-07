"""
AniVault Constants Module

This module provides centralized constants for the AniVault application.
All magic values and configuration constants are defined here to ensure
consistency and maintainability across the codebase.

The constants are organized in a hierarchical structure with parent-child relationships
to eliminate duplication and provide a single source of truth.
"""

# Import all constant classes for direct access
from .api import APIConfig
from .api import CacheConfig as APICacheConfig
from .api import TMDBConfig
from .api_fields import APIFields
from .cli import BatchConfig
from .cli import CacheConfig as CLICacheConfig
from .cli import (
    CLICommands,
    CLIDefaults,
    CLIFormatting,
    CLIHelp,
    CLIMessages,
    CLIOptions,
    ConfidenceConfig,
)
from .cli import LogConfig as CLILogConfig
from .cli import QueueConfig, RunDefaults, WorkerConfig
from .core import BusinessRules
from .core import CacheConfig as CoreCacheConfig
from .core import NormalizationConfig, ProcessingConfig
from .file_formats import (
    ExclusionPatterns,
    FileLimits,
    MetadataConfig,
    SubtitleFormats,
    TestConfig,
    VideoFormats,
)
from .gui_messages import (
    ButtonTexts,
    DialogMessages,
    DialogTitles,
    PlaceholderTexts,
    ProgressMessages,
    StatusMessages,
    ToolTips,
)
from .logging import ErrorLogging
from .logging import LogConfig as LoggingConfig
from .logging import LogLevels, LogMessages, LogPaths, PerformanceLogging
from .matching import (
    ConfidenceThresholds,
    FallbackStrategy,
    MatchingAlgorithm,
    ScoringWeights,
    TitleNormalization,
    ValidationConfig,
)
from .network import DownloadConfig, NetworkConfig
from .tmdb_messages import TMDBErrorMessages, TMDBOperationNames

# Import system classes for direct access
from .system import (
    CLI,
    TMDB,
    Application,
    Batch,
    Boolean,
    Cache,
    Config,
    Encoding,
    EnrichmentStatus,
    ErrorHandling,
    FileSystem,
    JsonKeys,
    Language,
    Logging,
    MediaType,
    Memory,
    Performance,
    Pipeline,
    Process,
    Status,
    Timeout,
    TMDBErrorHandling,
)

# Export all classes and constants
__all__ = [
    "CLI",
    "TMDB",
    "APIConfig",
    "APIFields",
    "Application",
    "Batch",
    "BatchConfig",
    "Boolean",
    "BusinessRules",
    "ButtonTexts",
    "CLICacheConfig",
    "CLICommands",
    "CLIDefaults",
    "CLIFormatting",
    "CLIHelp",
    "CLILogConfig",
    "CLIMessages",
    "CLIOptions",
    "Cache",
    "ConfidenceConfig",
    "ConfidenceThresholds",
    "Config",
    "CoreCacheConfig",
    "DialogMessages",
    "DialogTitles",
    "DownloadConfig",
    "Encoding",
    "EnrichmentStatus",
    "ErrorHandling",
    "ErrorLogging",
    "ExclusionPatterns",
    "FallbackStrategy",
    "FileLimits",
    "FileSystem",
    "JsonKeys",
    "Language",
    "LogLevels",
    "LogMessages",
    "LogPaths",
    "Logging",
    "LoggingConfig",
    "MatchingAlgorithm",
    "MediaType",
    "Memory",
    "MetadataConfig",
    "NetworkConfig",
    "NormalizationConfig",
    "Performance",
    "PerformanceLogging",
    "Pipeline",
    "PlaceholderTexts",
    "Process",
    "ProcessingConfig",
    "ProgressMessages",
    "QueueConfig",
    "RunDefaults",
    "ScoringWeights",
    "Status",
    "StatusMessages",
    "SubtitleFormats",
    "TMDBConfig",
    "TMDBErrorHandling",
    "TMDBErrorMessages",
    "TMDBOperationNames",
    "TestConfig",
    "Timeout",
    "TitleNormalization",
    "ToolTips",
    "ValidationConfig",
    "VideoFormats",
    "WorkerConfig",
]
