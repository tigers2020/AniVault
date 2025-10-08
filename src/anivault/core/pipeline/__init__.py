"""Pipeline components for AniVault file processing.

This module contains the core pipeline components for processing anime files:
- BoundedQueue: Thread-safe queue with size limits for backpressure
- Statistics classes: For collecting pipeline metrics
- DirectoryScanner: For scanning directories for files
- ParserWorker: For processing files in parallel
- CacheV1: For caching processed results
"""

__version__ = "1.0.0"
