"""Compatibility shim for parser models."""

from anivault.core.parser.models.anitopy_models import AnitopyResult
from anivault.shared.models.parser import ParsingAdditionalInfo, ParsingResult

__all__ = ["AnitopyResult", "ParsingAdditionalInfo", "ParsingResult"]
