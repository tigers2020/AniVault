"""
Base Pydantic Models for AniVault

This module defines the foundation of AniVault's type system, providing
common Pydantic base models with standardized configuration.

Design Decisions:
- Pydantic over TypedDict: Runtime validation + JSON serialization
- Pydantic over dataclass: Built-in validation + mypy plugin support
- ConfigDict settings: Balance between strictness and API compatibility

Migration Strategy:
- All new models should inherit from BaseTypeModel or StrictModel
- Existing dict/Any usage will be gradually replaced via feature flags
- Legacy code can coexist during transition period
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BaseTypeModel(BaseModel):
    """Common base model for all AniVault types.

    This model provides lenient configuration suitable for external API
    boundaries (e.g., TMDB responses) where extra fields may appear.

    Configuration:
        - extra="ignore": Silently ignore unknown fields (API compatibility)
        - populate_by_name=True: Accept both field names and aliases
        - use_enum_values=True: Serialize enums as their values
        - arbitrary_types_allowed=False: Enforce Pydantic-compatible types
        - frozen=False: Allow field modification after creation

    Example:
        >>> class User(BaseTypeModel):
        ...     name: str
        ...     age: int
        ...
        >>> user = User(name="Alice", age=30, extra_field="ignored")
        >>> user.name
        'Alice'
        >>> user.age
        30
    """

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        use_enum_values=True,
        arbitrary_types_allowed=False,
        frozen=False,
    )


class StrictModel(BaseTypeModel):
    """Strict validation model for critical data structures.

    Use this for internal data structures where extra fields indicate
    programmer error rather than API evolution.

    Configuration:
        - extra="forbid": Raise ValidationError on unknown fields
        - validate_assignment=True: Validate on field modification
        - Other settings inherited from BaseTypeModel

    Example:
        >>> class Config(StrictModel):
        ...     api_key: str
        ...     timeout: int
        ...
        >>> config = Config(api_key="secret", timeout=30)  # OK
        >>> # ValidationError on extra field:
        >>> config = Config(api_key="secret", timeout=30, typo="oops")
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        populate_by_name=True,
        use_enum_values=True,
        arbitrary_types_allowed=False,
        frozen=False,
    )
