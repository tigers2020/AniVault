"""Unit tests for dataclass serialization utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

import pytest

from anivault.shared.utils.dataclass_serialization import from_dict, to_dict


@dataclass
class SimpleUser:
    """Simple user dataclass for testing."""

    name: str
    age: int


@dataclass
class UserWithTimestamps:
    """User dataclass with datetime and UUID fields."""

    name: str
    created_at: datetime
    user_id: UUID


@dataclass
class Address:
    """Address dataclass for nested testing."""

    street: str
    city: str
    zip_code: str


@dataclass
class UserWithAddress:
    """User dataclass with nested Address."""

    name: str
    age: int
    address: Address


@dataclass
class UserWithAddressDict:
    """User dataclass with dict of dataclasses."""

    name: str
    address_book: dict[str, Address]


@dataclass
class UserWithOptionalFields:
    """User dataclass with optional fields."""

    name: str
    age: int | None = None
    email: str | None = None
    nickname: str | None = None


@dataclass
class UserWithOptionalNested:
    """User dataclass with optional nested dataclass."""

    name: str
    address: Address | None = None


@dataclass
class UserWithAlias:
    """User dataclass with an alias field (Subtask 3.2)."""

    name: str
    age: int = field(metadata={"alias": "years"})
    email: str | None = None


@dataclass
class StrictUser:
    """Strict user dataclass for extra='forbid' testing (Subtask 3.3)."""

    name: str
    age: int


class TestToDict:
    """Tests for to_dict function."""

    def test_simple_dataclass(self):
        """Test converting simple dataclass to dict."""
        user = SimpleUser(name="Alice", age=30)
        result = to_dict(user)

        assert result == {"name": "Alice", "age": 30}

    def test_datetime_serialization(self):
        """Test datetime is converted to ISO string."""
        now = datetime(2023, 1, 1, 12, 0, 0)
        user = UserWithTimestamps(name="Alice", created_at=now, user_id=uuid4())
        result = to_dict(user)

        assert result["created_at"] == "2023-01-01T12:00:00"

    def test_uuid_serialization(self):
        """Test UUID is converted to string."""
        user_id = uuid4()
        user = UserWithTimestamps(
            name="Alice", created_at=datetime.now(), user_id=user_id
        )
        result = to_dict(user)

        assert result["user_id"] == str(user_id)

    def test_nested_dataclass(self):
        """Test converting nested dataclass to dict."""
        address = Address(street="123 Main St", city="Springfield", zip_code="12345")
        user = UserWithAddress(name="Bob", age=25, address=address)
        result = to_dict(user)

        assert result["name"] == "Bob"
        assert result["age"] == 25
        assert isinstance(result["address"], dict)
        assert result["address"]["street"] == "123 Main St"
        assert result["address"]["city"] == "Springfield"

    def test_non_dataclass_raises_error(self):
        """Test that non-dataclass raises TypeError."""
        with pytest.raises(TypeError, match="is not a dataclass"):
            to_dict({"not": "a dataclass"})


class TestFromDict:
    """Tests for from_dict function."""

    def test_simple_dataclass(self):
        """Test creating simple dataclass from dict."""
        data = {"name": "Alice", "age": 30}
        user = from_dict(SimpleUser, data)

        assert user.name == "Alice"
        assert user.age == 30

    def test_datetime_deserialization(self):
        """Test ISO string is converted back to datetime."""
        data = {
            "name": "Alice",
            "created_at": "2023-01-01T12:00:00",
            "user_id": "12345678-1234-1234-1234-123456789012",
        }
        user = from_dict(UserWithTimestamps, data)

        assert isinstance(user.created_at, datetime)
        assert user.created_at.year == 2023

    def test_uuid_deserialization(self):
        """Test UUID string is converted back to UUID object."""
        user_id = uuid4()
        data = {
            "name": "Alice",
            "created_at": "2023-01-01T12:00:00",
            "user_id": str(user_id),
        }
        user = from_dict(UserWithTimestamps, data)

        assert isinstance(user.user_id, UUID)
        assert user.user_id == user_id

    def test_nested_dataclass(self):
        """Test creating dataclass with nested dataclass from dict."""
        data = {
            "name": "Bob",
            "age": 25,
            "address": {
                "street": "123 Main St",
                "city": "Springfield",
                "zip_code": "12345",
            },
        }
        user = from_dict(UserWithAddress, data)

        assert user.name == "Bob"
        assert user.age == 25
        assert isinstance(user.address, Address)
        assert user.address.street == "123 Main St"
        assert user.address.city == "Springfield"

    def test_non_dataclass_raises_error(self):
        """Test that non-dataclass raises TypeError."""
        with pytest.raises(TypeError, match="is not a dataclass"):
            from_dict(dict, {"test": "data"})

    def test_missing_required_field_raises_error(self):
        """Test that missing required field raises KeyError."""
        data = {"name": "Alice"}  # missing 'age'

        with pytest.raises(KeyError, match="Missing required field"):
            from_dict(SimpleUser, data)

    def test_alias_field(self):
        """Test creating dataclass with field alias (Subtask 3.2)."""
        data = {"name": "Iris", "years": 28, "email": "iris@example.com"}
        user = from_dict(UserWithAlias, data)

        assert user.name == "Iris"
        assert user.age == 28  # Alias 'years' maps to 'age'
        assert user.email == "iris@example.com"

    def test_alias_field_with_name(self):
        """Test that field name also works even if alias is defined."""
        data = {"name": "Jack", "age": 29, "email": "jack@example.com"}
        user = from_dict(UserWithAlias, data)

        assert user.name == "Jack"
        assert user.age == 29
        assert user.email == "jack@example.com"

    def test_strict_dataclass_extra_fields_forbidden(self):
        """Test that extra fields are rejected for strict dataclasses (Subtask 3.3)."""
        data = {"name": "Alice", "age": 30, "extra_field": "not allowed"}

        with pytest.raises(TypeError, match="Extra fields not allowed"):
            from_dict(StrictUser, data, extra="forbid")


class TestRoundTrip:
    """Tests for round-trip serialization (to_dict -> from_dict)."""

    def test_simple_round_trip(self):
        """Test round-trip for simple dataclass."""
        original = SimpleUser(name="Alice", age=30)
        data = to_dict(original)
        restored = from_dict(SimpleUser, data)

        assert restored == original

    def test_datetime_round_trip(self):
        """Test round-trip for datetime field."""
        original = UserWithTimestamps(
            name="Alice",
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            user_id=uuid4(),
        )
        data = to_dict(original)
        restored = from_dict(UserWithTimestamps, data)

        assert restored.name == original.name
        assert restored.created_at == original.created_at
        assert restored.user_id == original.user_id

    def test_nested_dataclass_round_trip(self):
        """Test round-trip for nested dataclass."""
        address = Address(street="123 Main St", city="Springfield", zip_code="12345")
        original = UserWithAddress(name="Bob", age=25, address=address)
        data = to_dict(original)
        restored = from_dict(UserWithAddress, data)

        assert restored == original
        assert isinstance(restored.address, Address)
        assert restored.address.street == original.address.street

    def test_dict_of_dataclasses_round_trip(self):
        """Test round-trip for dict of dataclasses."""
        address_book = {
            "home": Address(street="123 Main St", city="NYC", zip_code="10001"),
            "work": Address(street="456 Oak Ave", city="LA", zip_code="90001"),
        }
        original = UserWithAddressDict(name="Frank", address_book=address_book)
        data = to_dict(original)
        restored = from_dict(UserWithAddressDict, data)

        assert isinstance(restored.address_book["home"], Address)
        assert restored.address_book["home"].city == original.address_book["home"].city

    def test_optional_fields_round_trip(self):
        """Test round-trip for optional fields."""
        original = UserWithOptionalFields(
            name="Grace", age=35, email="grace@example.com"
        )
        data = to_dict(original)
        restored = from_dict(UserWithOptionalFields, data)

        assert restored == original

    def test_optional_fields_with_none_round_trip(self):
        """Test round-trip for optional fields with None values."""
        original = UserWithOptionalFields(name="Henry")
        data = to_dict(original)
        restored = from_dict(UserWithOptionalFields, data)

        assert restored == original

    def test_optional_nested_round_trip(self):
        """Test round-trip for optional nested dataclass."""
        address = Address(street="789 Elm St", city="Chicago", zip_code="60601")
        original = UserWithOptionalNested(name="Ivy", address=address)
        data = to_dict(original)
        restored = from_dict(UserWithOptionalNested, data)

        assert restored == original
        assert isinstance(restored.address, Address)

    def test_optional_nested_none_round_trip(self):
        """Test round-trip for optional nested dataclass with None."""
        original = UserWithOptionalNested(name="Jack")
        data = to_dict(original)
        restored = from_dict(UserWithOptionalNested, data)

        assert restored == original
        assert restored.address is None
