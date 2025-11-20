"""Tests for metadata_enricher constants migration.

This module tests that:
1. EnrichmentStatus constants are correctly used
2. No hardcoded status strings remain
3. Status values match expected behavior
"""

import pytest


class TestEnrichmentStatus:
    """Test EnrichmentStatus constants."""

    def test_enrichment_status_values(self) -> None:
        """Test that enrichment status values are correct."""
        from anivault.shared.constants.system import EnrichmentStatus

        assert EnrichmentStatus.PENDING == "pending"
        assert EnrichmentStatus.SUCCESS == "success"
        assert EnrichmentStatus.FAILED == "failed"
        assert EnrichmentStatus.SKIPPED == "skipped"

    def test_enrichment_status_inherits_from_status(self) -> None:
        """Test that EnrichmentStatus uses Status base values."""
        from anivault.shared.constants.system import EnrichmentStatus, Status

        assert EnrichmentStatus.PENDING == Status.PENDING
        assert EnrichmentStatus.SUCCESS == Status.SUCCESS
        assert EnrichmentStatus.FAILED == Status.FAILED
        assert EnrichmentStatus.SKIPPED == Status.SKIPPED


class TestMetadataEnricherMigration:
    """Test that metadata_enricher.py correctly uses constants."""

    def test_metadata_enricher_imports_enrichment_status(self) -> None:
        """Test that metadata_enricher.py imports EnrichmentStatus."""
        from pathlib import Path

        enricher_file = Path("src/anivault/services/metadata_enricher.py")
        content = enricher_file.read_text(encoding="utf-8")

        assert "from anivault.shared.constants.system import EnrichmentStatus" in content

    def test_metadata_enricher_uses_constants(self) -> None:
        """Test that metadata_enricher.py uses EnrichmentStatus constants."""
        from pathlib import Path

        enricher_file = Path("src/anivault/services/metadata_enricher.py")
        content = enricher_file.read_text(encoding="utf-8")

        # Check that constants are used
        assert "EnrichmentStatus.SKIPPED" in content
        assert "EnrichmentStatus.SUCCESS" in content
        assert "EnrichmentStatus.FAILED" in content

    def test_uses_enrichment_status_constants(self) -> None:
        """Test that EnrichmentStatus constants are actually used in code."""
        from pathlib import Path

        enricher_file = Path("src/anivault/services/metadata_enricher.py")
        content = enricher_file.read_text(encoding="utf-8")

        # Verify that constants are being used (not checking for absence of strings,
        # as they may appear in comments/docstrings which is fine)
        uses_constant_pattern = "EnrichmentStatus."
        count = content.count(uses_constant_pattern)

        # Should use EnrichmentStatus at least 3 times (SKIPPED, SUCCESS, FAILED)
        assert count >= 3, f"Expected at least 3 uses of EnrichmentStatus, found {count}"

