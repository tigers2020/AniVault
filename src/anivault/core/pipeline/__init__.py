"""Pipeline components for AniVault file processing.

This module contains the core pipeline components for processing anime files:
- run_pipeline: Main orchestration function for running the complete pipeline
- BoundedQueue: Thread-safe queue with size limits for backpressure
- Statistics classes: For collecting pipeline metrics
- DirectoryScanner: For scanning directories for files
- ParserWorker: For processing files in parallel
- CacheV1: For caching processed results

Recommended imports:
    from anivault.core.pipeline import run_pipeline
    from anivault.core.pipeline.domain import PipelineFactory
    from anivault.core.pipeline.components import DirectoryScanner, ParserWorkerPool
"""

from anivault.core.pipeline.domain.orchestrator import run_pipeline

__all__ = ["run_pipeline"]
__version__ = "1.0.0"
