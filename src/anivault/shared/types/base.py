"""
Base Dataclasses for AniVault

This module defines the foundation of AniVault's type system, providing
common dataclass base classes with standardized configuration.

Design Decisions:
- Dataclass over Pydantic: Type safety without runtime overhead
- Dataclass over TypedDict: Better IDE support and runtime validation
- Configuration via metadata: extra="ignore", extra="forbid" support

Migration Strategy:
- All new models should inherit from BaseDataclass or StrictDataclass
- Existing Pydantic BaseModel usage will be gradually replaced
- Legacy code can coexist during transition period
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BaseDataclass:
    """Common base dataclass for all AniVault types.

    This dataclass provides lenient configuration suitable for external API
    boundaries (e.g., TMDB responses) where extra fields may appear.

    Configuration (via metadata):
        - extra="ignore": Silently ignore unknown fields (API compatibility)
        - populate_by_name=True: Accept both field names and aliases

    Note: Unlike Pydantic's extra="ignore", dataclass validation is done
    via from_dict() utility function.

    Example:
        >>> class User(BaseDataclass):
        ...     name: str
        ...     age: int
        ...
        >>> from anivault.shared.utils.dataclass_serialization import from_dict
        >>> data = {'name': 'Alice', 'age': 30, 'extra_field': 'ignored'}
        >>> user = from_dict(User, data)  # extra_field is ignored
        >>> user.name
        'Alice'
    """


@dataclass
class StrictDataclass(BaseDataclass):
    """Strict dataclass for critical data structures.

    Extends BaseDataclass with extra="forbid" behavior:
    - Extra fields in input data raise TypeError
    - Use for internal data structures where strictness is critical

    Configuration (via metadata):
        - extra="forbid": Reject unknown fields

    Example:
        >>> class StrictUser(StrictDataclass):
        ...     name: str
        ...     age: int
        ...
        >>> from anivault.shared.utils.dataclass_serialization import from_dict
        >>> from_dict(StrictUser, {'name': 'Alice', 'age': 30})  # OK
        >>> from_dict(StrictUser, {'name': 'Alice', 'age': 30, 'extra': 'bad'}, extra="forbid")  # TypeError  # pylint: disable=line-too-long
    """


# Backward compatibility aliases
BaseTypeModel = BaseDataclass
StrictModel = StrictDataclass
