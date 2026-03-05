"""Shared parser output models for AniVault.

Re-exports from domain.entities for backward compatibility.
"""

from __future__ import annotations

from anivault.domain.entities.parser import ParsingAdditionalInfo, ParsingResult

__all__ = ["ParsingAdditionalInfo", "ParsingResult"]
