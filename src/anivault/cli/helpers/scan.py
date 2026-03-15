"""Scan command helper functions.

Formatter/util only — no UseCase, no services, no orchestration.
Scan pipeline execution and metadata enrichment live in scan_handler.py.
"""

from __future__ import annotations

from anivault.shared.models.metadata import FileMetadata
from anivault.shared.types.metadata_types import FileMetadataDict
from anivault.shared.utils.metadata_converter import MetadataConverter

from .scan_formatters import collect_scan_data, display_scan_results

__all__ = [
    "collect_scan_data",
    "display_scan_results",
    "file_metadata_to_dict",
    "dict_to_file_metadata",
]


def dict_to_file_metadata(result: FileMetadataDict) -> FileMetadata:
    """Convert FileMetadataDict to FileMetadata.

    Args:
        result: FileMetadataDict containing file metadata

    Returns:
        FileMetadata instance
    """
    return MetadataConverter.from_dict(result)


def file_metadata_to_dict(metadata: FileMetadata) -> FileMetadataDict:
    """Convert FileMetadata to JSON-serializable dict.

    Args:
        metadata: FileMetadata instance to convert

    Returns:
        FileMetadataDict suitable for JSON output
    """
    return MetadataConverter.to_dict(metadata)


# Backward-compat aliases used by scan_handler (camelCase private names preserved)
_dict_to_file_metadata = dict_to_file_metadata
_file_metadata_to_dict = file_metadata_to_dict
