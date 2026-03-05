"""System configuration constants (compatibility shim)."""

from .system.application import (
    Application,
    Boolean,
    Config,
    EnrichmentStatus,
    FolderDefaults,
    JsonKeys,
    Language,
    MediaType,
    Status,
)
from .system.base import BASE_FILE_SIZE, BASE_HOUR, BASE_MINUTE, BASE_SECOND
from .system.cache import Cache
from .system.cli import CLI
from .system.filesystem import Encoding, FileSystem
from .system.logging import ErrorHandling, Logging
from .system.performance import Batch, Memory, Performance, Process, Timeout
from .system.pipeline import Pipeline
from .system.tmdb import TMDB, TMDBErrorHandling

__all__ = [
    "BASE_FILE_SIZE",
    "BASE_HOUR",
    "BASE_MINUTE",
    "BASE_SECOND",
    "CLI",
    "TMDB",
    "Application",
    "Batch",
    "Boolean",
    "Cache",
    "Config",
    "Encoding",
    "EnrichmentStatus",
    "ErrorHandling",
    "FileSystem",
    "FolderDefaults",
    "JsonKeys",
    "Language",
    "Logging",
    "MediaType",
    "Memory",
    "Performance",
    "Pipeline",
    "Process",
    "Status",
    "TMDBErrorHandling",
    "Timeout",
]
