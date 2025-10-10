"""Tests for ModelConverter utilities.

This module tests the type conversion utilities that bridge dict/Any
legacy code with type-safe Pydantic models.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from anivault.services.tmdb_models import TMDBGenre
from anivault.shared.errors import TypeCoercionError
from anivault.shared.types import BaseTypeModel
from anivault.shared.types.conversion import ModelConverter


class SimpleModel(BaseTypeModel):
    """Test model for conversion tests."""

    id: int
    name: str
    value: float | None = None


class TestModelConverter:
    """Test suite for ModelConverter class."""

    def test_to_model_success(self) -> None:
        """Test successful dict to model conversion."""
        # Given
        data = {"id": 1, "name": "Test", "value": 42.0}

        # When
        result = ModelConverter.to_model(data, SimpleModel)

        # Then
        assert isinstance(result, SimpleModel)
        assert result.id == 1
        assert result.name == "Test"
        assert result.value == 42.0

    def test_to_model_ignores_extra_fields(self) -> None:
        """Test that extra fields are ignored (BaseTypeModel behavior)."""
        # Given
        data = {"id": 1, "name": "Test", "extra_field": "ignored"}

        # When
        result = ModelConverter.to_model(data, SimpleModel)

        # Then
        assert isinstance(result, SimpleModel)
        assert result.id == 1
        assert result.name == "Test"
        assert not hasattr(result, "extra_field")

    def test_to_model_validation_error(self) -> None:
        """Test that validation errors are properly wrapped."""
        # Given
        invalid_data = {"id": "not_an_int", "name": "Test"}

        # When & Then
        with pytest.raises(TypeCoercionError) as exc_info:
            ModelConverter.to_model(invalid_data, SimpleModel)

        error = exc_info.value
        assert error.model_name == "SimpleModel"
        assert len(error.validation_errors) > 0
        assert "validation error(s)" in error.message

    def test_to_model_missing_required_field(self) -> None:
        """Test error when required field is missing."""
        # Given
        incomplete_data = {"id": 1}  # Missing 'name'

        # When & Then
        with pytest.raises(TypeCoercionError) as exc_info:
            ModelConverter.to_model(incomplete_data, SimpleModel)

        error = exc_info.value
        assert "validation error(s)" in error.message

    def test_to_dict_basic(self) -> None:
        """Test model to dict conversion."""
        # Given
        model = SimpleModel(id=1, name="Test", value=42.0)

        # When
        result = ModelConverter.to_dict(model)

        # Then
        assert isinstance(result, dict)
        assert result["id"] == 1
        assert result["name"] == "Test"
        assert result["value"] == 42.0

    def test_to_dict_exclude_none(self) -> None:
        """Test that None values are excluded by default."""
        # Given
        model = SimpleModel(id=1, name="Test", value=None)

        # When
        result = ModelConverter.to_dict(model, exclude_none=True)

        # Then
        assert "value" not in result
        assert result["id"] == 1
        assert result["name"] == "Test"

    def test_to_dict_include_none(self) -> None:
        """Test that None values can be included."""
        # Given
        model = SimpleModel(id=1, name="Test", value=None)

        # When
        result = ModelConverter.to_dict(model, exclude_none=False)

        # Then
        assert "value" in result
        assert result["value"] is None

    def test_to_json_bytes(self) -> None:
        """Test orjson serialization to bytes."""
        # Given
        model = SimpleModel(id=1, name="Test", value=42.0)

        # When
        result = ModelConverter.to_json_bytes(model)

        # Then
        assert isinstance(result, bytes)
        assert b'"id":1' in result
        assert b'"name":"Test"' in result
        assert b'"value":42.0' in result

    def test_to_json_str(self) -> None:
        """Test orjson serialization to string."""
        # Given
        model = SimpleModel(id=1, name="Test", value=42.0)

        # When
        result = ModelConverter.to_json_str(model)

        # Then
        assert isinstance(result, str)
        assert '"id":1' in result
        assert '"name":"Test"' in result
        assert '"value":42.0' in result

    def test_try_validate_success(self) -> None:
        """Test successful validation with try_validate."""
        # Given
        data = {"id": 1, "name": "Test"}

        # When
        result = ModelConverter.try_validate(data, SimpleModel)

        # Then
        assert result is not None
        assert isinstance(result, SimpleModel)
        assert result.id == 1

    def test_try_validate_failure(self) -> None:
        """Test that try_validate returns None on failure."""
        # Given
        invalid_data = {"id": "not_an_int"}

        # When
        result = ModelConverter.try_validate(invalid_data, SimpleModel)

        # Then
        assert result is None


class TestModelConverterRealWorld:
    """Test ModelConverter with real TMDB models."""

    def test_tmdb_genre_conversion(self) -> None:
        """Test conversion with real TMDBGenre model."""
        # Given
        data = {"id": 16, "name": "Animation"}

        # When
        genre = ModelConverter.to_model(data, TMDBGenre)

        # Then
        assert isinstance(genre, TMDBGenre)
        assert genre.id == 16
        assert genre.name == "Animation"

    def test_tmdb_genre_roundtrip(self) -> None:
        """Test roundtrip conversion (dict → model → dict)."""
        # Given
        original_data = {"id": 16, "name": "Animation"}

        # When
        genre = ModelConverter.to_model(original_data, TMDBGenre)
        result_data = ModelConverter.to_dict(genre)

        # Then
        assert result_data == original_data


@pytest.mark.benchmark(group="converter")
class TestModelConverterPerformance:
    """Performance benchmarks for ModelConverter.

    Target: <10ms per conversion for typical models
    """

    def test_benchmark_to_model(self, benchmark) -> None:
        """Benchmark dict to model conversion."""
        # Given
        data = {"id": 16, "name": "Animation"}

        # When
        result = benchmark(ModelConverter.to_model, data, TMDBGenre)

        # Then
        assert result.id == 16
        # Performance assertion checked by pytest-benchmark

    def test_benchmark_to_dict(self, benchmark) -> None:
        """Benchmark model to dict conversion."""
        # Given
        model = TMDBGenre(id=16, name="Animation")

        # When
        result = benchmark(ModelConverter.to_dict, model)

        # Then
        assert result["id"] == 16
        # Performance assertion checked by pytest-benchmark

    def test_benchmark_to_json_bytes(self, benchmark) -> None:
        """Benchmark model to JSON bytes conversion."""
        # Given
        model = TMDBGenre(id=16, name="Animation")

        # When
        result = benchmark(ModelConverter.to_json_bytes, model)

        # Then
        assert isinstance(result, bytes)
        # Performance assertion checked by pytest-benchmark

    def test_benchmark_roundtrip(self, benchmark) -> None:
        """Benchmark full roundtrip (dict → model → dict)."""
        # Given
        data = {"id": 16, "name": "Animation"}

        # When
        def roundtrip():
            model = ModelConverter.to_model(data, TMDBGenre)
            return ModelConverter.to_dict(model)

        result = benchmark(roundtrip)

        # Then
        assert result == data
        # Performance assertion checked by pytest-benchmark
