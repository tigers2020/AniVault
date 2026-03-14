"""Compatibility shim for parser models.

DEPRECATED: Prefer ``from anivault.shared.models.parser import ParsingResult``
or ``from anivault.core.parser.models import ParsingResult``.
This module is kept for backward compatibility and may be removed in a future release.
"""

from anivault.shared.models.parser import ParsingResult

__all__ = ["ParsingResult"]
