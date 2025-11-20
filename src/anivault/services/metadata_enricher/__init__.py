"""Metadata enricher package exports.

This package provides scoring models and protocols for metadata enrichment.
The main MetadataEnricher service is also re-exported here from the parent module.

Note: Due to naming conflict between metadata_enricher.py and metadata_enricher/,
we use importlib to load the module directly.
"""

# Import submodules
# Re-export MetadataEnricher from parent enricher.py module
from anivault.services.enricher import MetadataEnricher

from .batch_processor import BatchProcessor, BatchSummary
from .fetcher import TMDBFetcher
from .models import EnrichedMetadata, MatchEvidence, ScoreResult
from .scoring import BaseScorer
from .transformer import MetadataTransformer

__all__ = [
    "BaseScorer",
    "BatchProcessor",
    "BatchSummary",
    "EnrichedMetadata",
    "MatchEvidence",
    "MetadataEnricher",
    "MetadataTransformer",
    "ScoreResult",
    "TMDBFetcher",
]
