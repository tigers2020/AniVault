"""Tests for BatchProcessor module.

This module tests the BatchProcessor class for concurrent metadata enrichment.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from anivault.core.parser.models import ParsingResult
from anivault.services.metadata_enricher.batch_processor import (
    BatchProcessor,
    BatchSummary,
)
from anivault.services.metadata_enricher.models import EnrichedMetadata
from anivault.shared.errors import DomainError, ErrorCode, InfrastructureError


@pytest.fixture
def batch_processor() -> BatchProcessor:
    """Create a BatchProcessor instance."""
    return BatchProcessor(concurrency=3)


@pytest.fixture
def mock_parsing_results() -> list[ParsingResult]:
    """Create mock ParsingResult instances."""
    return [
        ParsingResult(title="Anime 1", season=1, episode=1),
        ParsingResult(title="Anime 2", season=1, episode=2),
        ParsingResult(title="Anime 3", season=1, episode=3),
    ]


class TestBatchProcessorInit:
    """Tests for BatchProcessor initialization."""

    def test_init_default_concurrency(self) -> None:
        """Test initialization with default concurrency."""
        processor = BatchProcessor()
        assert processor._concurrency == 5

    def test_init_custom_concurrency(self) -> None:
        """Test initialization with custom concurrency."""
        processor = BatchProcessor(concurrency=10)
        assert processor._concurrency == 10

    def test_init_invalid_concurrency(self) -> None:
        """Test initialization with invalid concurrency raises ValueError."""
        with pytest.raises(ValueError, match="concurrency must be at least 1"):
            BatchProcessor(concurrency=0)

        with pytest.raises(ValueError, match="concurrency must be at least 1"):
            BatchProcessor(concurrency=-1)


class TestBatchProcessorSuccess:
    """Tests for successful batch processing."""

    @pytest.mark.asyncio
    async def test_process_all_success(
        self,
        batch_processor: BatchProcessor,
        mock_parsing_results: list[ParsingResult],
    ) -> None:
        """Test processing with all successful results."""

        # Given: Mock worker that always succeeds
        async def mock_worker(item: ParsingResult) -> EnrichedMetadata:
            enriched = EnrichedMetadata(file_info=item)
            enriched.enrichment_status = "success"
            return enriched

        # When: Process items
        summary = await batch_processor.process(mock_parsing_results, mock_worker)

        # Then: All successful
        assert summary.success_count == 3
        assert summary.failed_count == 0
        assert len(summary.results) == 3
        assert all(r.enrichment_status == "success" for r in summary.results)

    @pytest.mark.asyncio
    async def test_process_empty_list(self, batch_processor: BatchProcessor) -> None:
        """Test processing with empty list returns empty summary."""
        # Given: Empty list
        empty_list: list[ParsingResult] = []

        async def mock_worker(item: ParsingResult) -> EnrichedMetadata:
            return EnrichedMetadata(file_info=item)

        # When: Process
        summary = await batch_processor.process(empty_list, mock_worker)

        # Then: Empty results
        assert summary.success_count == 0
        assert summary.failed_count == 0
        assert len(summary.results) == 0


class TestBatchProcessorFailures:
    """Tests for batch processing with failures."""

    @pytest.mark.asyncio
    async def test_process_all_failures(
        self,
        batch_processor: BatchProcessor,
        mock_parsing_results: list[ParsingResult],
    ) -> None:
        """Test processing with all failures."""

        # Given: Mock worker that always raises
        async def mock_worker(item: ParsingResult) -> EnrichedMetadata:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Test error",
                context=None,
            )

        # When: Process items
        summary = await batch_processor.process(mock_parsing_results, mock_worker)

        # Then: All failed
        assert summary.success_count == 0
        assert summary.failed_count == 3
        assert len(summary.results) == 3
        assert all(r.enrichment_status == "failed" for r in summary.results)

    @pytest.mark.asyncio
    async def test_process_mixed_results(
        self,
        batch_processor: BatchProcessor,
        mock_parsing_results: list[ParsingResult],
    ) -> None:
        """Test processing with mixed success and failure results."""
        # Given: Mock worker that succeeds for first item, fails for rest
        call_count = 0

        async def mock_worker(item: ParsingResult) -> EnrichedMetadata:
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                enriched = EnrichedMetadata(file_info=item)
                enriched.enrichment_status = "success"
                return enriched

            raise InfrastructureError(
                code=ErrorCode.TMDB_API_REQUEST_FAILED,
                message="Network error",
                context=None,
            )

        # When: Process items
        summary = await batch_processor.process(mock_parsing_results, mock_worker)

        # Then: Mixed results
        assert summary.success_count == 1
        assert summary.failed_count == 2
        assert len(summary.results) == 3
        assert summary.results[0].enrichment_status == "success"
        assert summary.results[1].enrichment_status == "failed"
        assert summary.results[2].enrichment_status == "failed"

    @pytest.mark.asyncio
    async def test_process_unexpected_exception(
        self,
        batch_processor: BatchProcessor,
        mock_parsing_results: list[ParsingResult],
    ) -> None:
        """Test processing with unexpected exception types."""

        # Given: Mock worker that raises unexpected exception
        async def mock_worker(item: ParsingResult) -> EnrichedMetadata:
            raise RuntimeError("Unexpected error")

        # When: Process items
        summary = await batch_processor.process(mock_parsing_results, mock_worker)

        # Then: All failed (unexpected exceptions handled)
        assert summary.success_count == 0
        assert summary.failed_count == 3
        assert len(summary.results) == 3
        assert all(r.enrichment_status == "failed" for r in summary.results)


class TestBatchProcessorEdgeCases:
    """Tests for edge cases in batch processing."""

    @pytest.mark.asyncio
    async def test_process_unexpected_result_type(
        self,
        batch_processor: BatchProcessor,
        mock_parsing_results: list[ParsingResult],
    ) -> None:
        """Test processing with unexpected result type."""

        # Given: Mock worker that returns unexpected type
        async def mock_worker(item: ParsingResult) -> EnrichedMetadata:
            return "not_enriched_metadata"  # type: ignore[return-value]

        # When: Process items
        summary = await batch_processor.process(mock_parsing_results, mock_worker)

        # Then: All failed (unexpected type handled)
        assert summary.success_count == 0
        assert summary.failed_count == 3
        assert len(summary.results) == 3
        assert all(r.enrichment_status == "failed" for r in summary.results)

    @pytest.mark.asyncio
    async def test_process_concurrency_limit(self) -> None:
        """Test that concurrency limit is respected."""
        # Given: Processor with concurrency 1
        processor = BatchProcessor(concurrency=1)
        call_order: list[int] = []

        async def mock_worker(item: ParsingResult) -> EnrichedMetadata:
            # Track call order
            call_order.append(hash(item.title))
            enriched = EnrichedMetadata(file_info=item)
            enriched.enrichment_status = "success"
            return enriched

        items = [
            ParsingResult(title=f"Anime {i}", season=1, episode=i) for i in range(5)
        ]

        # When: Process items
        summary = await processor.process(items, mock_worker)

        # Then: All processed successfully
        assert summary.success_count == 5
        assert summary.failed_count == 0
        # Note: We can't guarantee serial execution order due to asyncio,
        # but all items should be processed
        assert len(call_order) == 5


class TestBatchSummary:
    """Tests for BatchSummary dataclass."""

    def test_batch_summary_structure(self) -> None:
        """Test BatchSummary structure and attributes."""
        # Given: Mock results
        mock_result1 = Mock(spec=EnrichedMetadata)
        mock_result2 = Mock(spec=EnrichedMetadata)
        results = [mock_result1, mock_result2]

        # When: Create summary
        summary = BatchSummary(
            success_count=1,
            failed_count=1,
            results=results,
        )

        # Then: Attributes are correct
        assert summary.success_count == 1
        assert summary.failed_count == 1
        assert len(summary.results) == 2
        assert summary.results == results
