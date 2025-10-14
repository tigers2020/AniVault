"""Main pipeline orchestrator facade (backward compatibility).

.. deprecated:: 1.0.0
    This module is deprecated. Use one of the following imports instead:

    **Recommended:**
        from anivault.core.pipeline import run_pipeline

    **Alternative:**
        from anivault.core.pipeline.domain import run_pipeline
        from anivault.core.pipeline.domain.orchestrator import run_pipeline

    **Legacy (still works, but discouraged):**
        from anivault.core.pipeline.main import run_pipeline

This facade maintains backward compatibility for existing code.
The old import path will be supported for 2 major versions, but new code
should use the recommended import paths above.

Migration Guide:
    Old code::

        from anivault.core.pipeline.main import run_pipeline
        results = run_pipeline("/path/to/anime", [".mkv", ".mp4"])

    New code::

        from anivault.core.pipeline import run_pipeline  # Recommended!
        results = run_pipeline("/path/to/anime", [".mkv", ".mp4"])

See Also:
    - Migration Guide: docs/migration/pipeline-refactoring.md
    - Architecture: docs/architecture/pipeline.md
"""

from __future__ import annotations

from anivault.core.pipeline.domain.orchestrator import run_pipeline

__all__ = ["run_pipeline"]
