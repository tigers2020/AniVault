"""
AniVault Constants Module

This module provides centralized constants for the AniVault application.
All magic values and configuration constants are defined here to ensure
consistency and maintainability across the codebase.

The constants are organized in a hierarchical structure with parent-child relationships
to eliminate duplication and provide a single source of truth.
"""

# Import all constant classes for direct access
from .api import (
    APIConfig,
    TMDBConfig,
)
from .api import (
    CacheConfig as APICacheConfig,
)
from .api_fields import (
    APIFields,
)
from .cli import (
    BatchConfig,
    CLICommands,
    CLIDefaults,
    CLIFormatting,
    CLIHelp,
    CLIMessages,
    CLIOptions,
    ConfidenceConfig,
    QueueConfig,
    RunDefaults,
    WorkerConfig,
)
from .cli import (
    CacheConfig as CLICacheConfig,
)
from .cli import (
    LogConfig as CLILogConfig,
)
from .core import (
    BusinessRules,
    NormalizationConfig,
    ProcessingConfig,
)
from .core import (
    CacheConfig as CoreCacheConfig,
)
from .file_formats import (
    ExclusionPatterns,
    FileLimits,
    MetadataConfig,
    SubtitleFormats,
    TestConfig,
    VideoFormats,
)
from .logging import (
    ErrorLogging,
    LogLevels,
    LogMessages,
    LogPaths,
    PerformanceLogging,
)
from .logging import (
    LogConfig as LoggingConfig,
)
from .matching import (
    ConfidenceThresholds,
    FallbackStrategy,
    MatchingAlgorithm,
    ScoringWeights,
    TitleNormalization,
    ValidationConfig,
)
from .network import (
    DownloadConfig,
    NetworkConfig,
)

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
    "CLICacheConfig",
    "CLICommands",
    "CLIDefaults",
    "CLIFormatting",
    "CLIHelp",
    "CLILogConfig",
    "CLIMessages",
    "CLIOptions",
    "Cache",
    "CoreCacheConfig",
    "ConfidenceConfig",
    "ConfidenceThresholds",
    "Config",
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
    "Process",
    "ProcessingConfig",
    "QueueConfig",
    "RunDefaults",
    "ScoringWeights",
    "Status",
    "SubtitleFormats",
    "TMDBConfig",
    "TMDBErrorHandling",
    "TestConfig",
    "Timeout",
    "TitleNormalization",
    "ValidationConfig",
    "VideoFormats",
    "WorkerConfig",
]
