"""Scan command helper functions.

This module contains the core business logic for the scan command,
extracted for better maintainability and reusability.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

from rich.console import Console

from anivault.app.use_cases.scan_use_case import ScanUseCase
from anivault.cli.progress import create_progress_manager
from anivault.core.parser.models import ParsingAdditionalInfo, ParsingResult
from anivault.services import RateLimitStateMachine, SemaphoreManager, TMDBClient, TokenBucketRateLimiter
from anivault.services.enricher import MetadataEnricher
from anivault.shared.constants import CLIDefaults, CLIFormatting, QueueConfig
from anivault.shared.constants.file_formats import VideoFormats
from anivault.shared.constants.scan_fields import ScanMessages
from anivault.shared.models.metadata import FileMetadata
from anivault.shared.types.metadata_types import FileMetadataDict, ParsingResultDict
from anivault.shared.utils.metadata_converter import MetadataConverter

from .scan_formatters import collect_scan_data, display_scan_results

logger = logging.getLogger(__name__)

# Re-export for backward compatibility (extracted to scan_formatters.py)
__all__ = [
    "collect_scan_data",
    "display_scan_results",
    "enrich_metadata",
    "run_scan_pipeline",
]


def _dict_to_file_metadata(result: FileMetadataDict) -> FileMetadata:
    """Convert FileMetadataDict to FileMetadata for compatibility.

    Args:
        result: FileMetadataDict containing file metadata

    Returns:
        FileMetadata instance with converted data
    """
    return MetadataConverter.from_dict(result)


def _file_metadata_to_dict(metadata: FileMetadata) -> FileMetadataDict:
    """Convert FileMetadata dataclass to JSON-serializable dict.

    This helper function converts a FileMetadata instance to a dictionary
    suitable for JSON output using MetadataConverter, maintaining backward
    compatibility with existing CLI JSON output format.

    Args:
        metadata: FileMetadata instance to convert

    Returns:
        FileMetadataDict (JSON-serializable dictionary)

    Example:
        >>> metadata = FileMetadata(
        ...     title="Attack on Titan",
        ...     file_path=Path("/anime/aot.mkv"),
        ...     file_type="mkv",
        ...     tmdb_id=1429,
        ... )
        >>> result = _file_metadata_to_dict(metadata)
        >>> isinstance(result, dict)
        True
    """
    return MetadataConverter.to_dict(metadata)


def run_scan_pipeline(
    directory: Path,
    console: Console,
    *,
    is_json_output: bool = False,
) -> list[FileMetadata]:
    """Run the file scanning pipeline.

    Args:
        directory: Directory to scan
        console: Rich console for output
        is_json_output: Whether JSON output is enabled

    Returns:
        List of FileMetadata instances containing scan results

    Raises:
        OSError: File system errors
        ValueError: Data processing errors
    """
    # Create progress manager (disabled for JSON output)
    progress_manager = create_progress_manager(disabled=is_json_output)

    # Run the file processing pipeline with progress display
    scan_use_case = ScanUseCase()
    with progress_manager.spinner("Scanning files..."):
        file_results = scan_use_case.execute(
            directory=directory,
            extensions=list(VideoFormats.ALL_EXTENSIONS),
            num_workers=CLIDefaults.DEFAULT_WORKER_COUNT,
            max_queue_size=QueueConfig.DEFAULT_SIZE,
        )

    if not is_json_output and file_results:
        console.print(
            CLIFormatting.format_colored_message(
                ScanMessages.SCAN_COMPLETED,
                "success",
            )
        )

    return file_results


def _file_metadata_to_parsing_result(metadata: FileMetadata) -> ParsingResult:
    """Convert FileMetadata to ParsingResult for enrichment.

    This helper function reconstructs a ParsingResult from FileMetadata.
    Note that some fields (quality, source, codec, audio, release_group)
    are not available in FileMetadata and will be set to None.

    Args:
        metadata: FileMetadata instance to convert

    Returns:
        ParsingResult instance for enrichment
    """
    additional_info = ParsingAdditionalInfo()
    return ParsingResult(
        title=metadata.title,
        episode=metadata.episode,
        season=metadata.season,
        year=metadata.year,
        quality=None,  # Not available in FileMetadata
        source=None,  # Not available in FileMetadata
        codec=None,  # Not available in FileMetadata
        audio=None,  # Not available in FileMetadata
        release_group=None,  # Not available in FileMetadata
        confidence=1.0,  # Assume high confidence for converted data
        parser_used="file_metadata_converter",
        additional_info=additional_info,
    )


async def enrich_metadata(
    file_results: list[FileMetadata],
    _console: Console,  # Reserved for future use
    *,
    is_json_output: bool = False,
) -> list[FileMetadata]:
    """Enrich file results with TMDB metadata.

    Args:
        file_results: List of FileMetadata instances to enrich
        _console: Rich console for output (reserved for future use)  # pylint: disable=unused-argument  # noqa: ARG002
        is_json_output: Whether JSON output is enabled

    Returns:
        List of enriched FileMetadata instances
    """
    if not file_results:
        return file_results

    # Initialize TMDB client
    rate_limiter = TokenBucketRateLimiter(
        capacity=10,  # Default rate limit
        refill_rate=10,  # Default refill rate
    )
    semaphore_manager = SemaphoreManager(
        concurrency_limit=CLIDefaults.DEFAULT_SCAN_CONCURRENCY,
    )
    state_machine = RateLimitStateMachine()

    tmdb_client = TMDBClient(
        rate_limiter=rate_limiter,
        semaphore_manager=semaphore_manager,
        state_machine=state_machine,
    )

    enricher = MetadataEnricher(tmdb_client=tmdb_client)

    # Create progress manager (disabled for JSON output)
    progress_manager = create_progress_manager(disabled=is_json_output)

    # Convert FileMetadata to ParsingResult for enrichment
    parsing_results = [_file_metadata_to_parsing_result(metadata) for metadata in file_results]

    # Enrich metadata
    enriched_metadata_list = []
    for parsing_result in progress_manager.track(
        parsing_results,
        "Enriching metadata...",
    ):
        enriched = await enricher.enrich_metadata(parsing_result)
        enriched_metadata_list.append(enriched)

    # Convert EnrichedMetadata back to FileMetadata
    enriched_file_results = []
    for metadata, enriched in zip(file_results, enriched_metadata_list):
        # Use EnrichedMetadata.to_file_metadata() to convert
        enriched_file_metadata = enriched.to_file_metadata(metadata.file_path)
        enriched_file_results.append(enriched_file_metadata)

    return enriched_file_results


def _extract_parsing_result_dict(parsing_result: ParsingResult) -> ParsingResultDict:
    """Extract parsing result as dictionary.

    This function converts a ParsingResult instance to its TypedDict representation
    using MetadataConverter for type safety.

    Args:
        parsing_result: ParsingResult instance to convert

    Returns:
        ParsingResultDict with parsing result data
    """
    return MetadataConverter.parsing_result_to_dict(parsing_result)


def _extract_enriched_metadata_dict(enriched_metadata: object) -> dict[str, object]:
    """Extract enriched metadata as dictionary.

    Note: This function is kept for backward compatibility but may be deprecated
    in favor of direct EnrichedMetadata model usage.

    Args:
        enriched_metadata: Enriched metadata object

    Returns:
        Dictionary with enriched metadata
    """
    # Type-safe access with fallback for backward compatibility
    if hasattr(enriched_metadata, "enrichment_status"):
        return {
            "enrichment_status": enriched_metadata.enrichment_status,
            "match_confidence": getattr(enriched_metadata, "match_confidence", None),
            "tmdb_data": getattr(enriched_metadata, "tmdb_data", None),
        }
    # Fallback for dict-like objects
    if isinstance(enriched_metadata, dict):
        return dict(enriched_metadata)
    # Fallback: convert to dict using asdict if dataclass
    if is_dataclass(enriched_metadata):
        return asdict(enriched_metadata)  # type: ignore[arg-type]
    return {}
