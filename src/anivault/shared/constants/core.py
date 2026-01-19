"""Core business logic constants (compatibility shim)."""

from __future__ import annotations

from .business.normalization import LanguageDetectionConfig, NormalizationConfig, SimilarityConfig
from .business.processing import ProcessingConfig
from .business.rules import BusinessRules

__all__ = [
    "BusinessRules",
    "LanguageDetectionConfig",
    "NormalizationConfig",
    "ProcessingConfig",
    "SimilarityConfig",
]
