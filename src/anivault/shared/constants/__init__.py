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
from .api import CacheValidationConstants, TMDBConfig
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
from .error_keys import ErrorCategoryValues, ErrorContextKeys, StatusValues
from .file_formats import (
    ExclusionPatterns,
    FileLimits,
    MetadataConfig,
    SubtitleFormats,
    TestConfig,
    VideoFormats,
    VideoQuality,
)
from .gui_messages import (
    ButtonTexts,
    DialogMessages,
    DialogTitles,
    PlaceholderTexts,
    ProgressMessages,
    StatusMessages,
    ToolTips,
    UIConfig,
)
from .http_codes import ContentTypes, HTTPHeaders, HTTPStatusCodes
from .logging import ErrorLogging
from .logging import LogConfig as LoggingConfig
from .logging import LogLevels, LogMessages, LogPaths, PerformanceLogging
from .logging_keys import LogContextKeys, LogFieldNames, LogOperationNames
from .matching import CacheConfig as MatchingCacheConfig
from .matching import (
    ConfidenceThresholds,
    DefaultLanguage,
    FallbackStrategy,
    GenreConfig,
    MatchingAlgorithm,
    MatchingFieldNames,
    ScoringWeights,
    TitleNormalization,
    ValidationConfig,
    ValidationConstants,
    YearMatchingConfig,
)
from .network import DownloadConfig, NetworkConfig

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
from .tmdb_keys import TMDBMediaTypes, TMDBResponseKeys, TMDBSearchKeys
from .tmdb_messages import TMDBErrorMessages, TMDBOperationNames

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
    "CacheValidationConstants",
    "ConfidenceConfig",
    "ConfidenceThresholds",
    "Config",
    "ContentTypes",
    "CoreCacheConfig",
    "DefaultLanguage",
    "DialogMessages",
    "DialogTitles",
    "DownloadConfig",
    "Encoding",
    "EnrichmentStatus",
    "ErrorCategoryValues",
    "ErrorContextKeys",
    "ErrorHandling",
    "ErrorLogging",
    "ExclusionPatterns",
    "FallbackStrategy",
    "FileLimits",
    "FileSystem",
    "GenreConfig",
    "HTTPHeaders",
    "HTTPStatusCodes",
    "JsonKeys",
    "Language",
    "LogContextKeys",
    "LogFieldNames",
    "LogLevels",
    "LogMessages",
    "LogOperationNames",
    "LogPaths",
    "Logging",
    "LoggingConfig",
    "MatchingAlgorithm",
    "MatchingCacheConfig",
    "MatchingFieldNames",
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
    "StatusValues",
    "SubtitleFormats",
    "TMDBConfig",
    "TMDBErrorHandling",
    "TMDBErrorMessages",
    "TMDBMediaTypes",
    "TMDBOperationNames",
    "TMDBResponseKeys",
    "TMDBSearchKeys",
    "TestConfig",
    "Timeout",
    "TitleNormalization",
    "ToolTips",
    "UIConfig",
    "ValidationConfig",
    "ValidationConstants",
    "VideoFormats",
    "VideoQuality",
    "WorkerConfig",
    "YearMatchingConfig",
]
