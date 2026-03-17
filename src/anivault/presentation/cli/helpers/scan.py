"""Scan command helper functions.

Formatter/util only — no UseCase, no services, no orchestration.
Scan pipeline execution and metadata enrichment live in scan_handler.py.

Phase 3: No MetadataConverter or shared.models usage. Consumes ScanResultItem DTO only.
"""

from __future__ import annotations

from .scan_formatters import collect_scan_data, display_scan_results

__all__ = [
    "collect_scan_data",
    "display_scan_results",
]
