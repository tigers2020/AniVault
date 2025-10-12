"""
API-related Type Definitions

This module provides type aliases and models for external API interactions,
primarily TMDB API responses.

Type Safety Strategy:
- Use constrained types (conint, constr) instead of plain primitives
- Define semantic aliases (TMDBId, ISODate) for domain clarity
- Provide runtime validation via Pydantic constraints
"""

from __future__ import annotations

from pydantic import conint, constr

# TMDB API type aliases
# Note: Using simple assignment instead of TypeAlias for Python 3.9 compatibility
TMDBId = conint(gt=0)  # Positive integer IDs
NonEmptyStr = constr(min_length=1, strip_whitespace=True)
ISODate = constr(pattern=r"^\d{4}-\d{2}-\d{2}$")  # YYYY-MM-DD format
LanguageCode = constr(pattern=r"^[a-z]{2}-[A-Z]{2}$")  # e.g., "ko-KR"

# NOTE: TypeAdapter examples will be added in Task 2 (Model Conversion Utilities)
# when needed for legacy code migration
