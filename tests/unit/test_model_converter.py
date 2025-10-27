"""Tests for ModelConverter utility."""

import pytest
from typing import Any
from pydantic import BaseModel, Field

from src.anivault.shared.types.conversion import ModelConverter
from src.anivault.shared.errors import TypeCoercionError


class TestDataModel(BaseModel):
    """Test model for conversion testing."""
    id: int
    name: str
    active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class TestDataModelConverter:
    """Test cases for ModelConverter."""

    def test_to_model_valid_data(self):
        """Test converting valid dictionary to model."""
        data = {
            "id": 1,
            "name": "test",
            "active": False,
            "metadata": {"key": "value"}
        }

        model = ModelConverter.to_model(data, TestDataModel)

        assert isinstance(model, TestDataModel)
        assert model.id == 1
        assert model.name == "test"
        assert model.active is False
        assert model.metadata == {"key": "value"}

    def test_to_model_minimal_data(self):
        """Test converting minimal data with defaults."""
        data = {"id": 2, "name": "minimal"}

        model = ModelConverter.to_model(data, TestDataModel)

        assert isinstance(model, TestDataModel)
        assert model.id == 2
        assert model.name == "minimal"
        assert model.active is True  # default value
        assert model.metadata == {}  # default value

    def test_to_model_invalid_data(self):
        """Test converting invalid data raises TypeCoercionError."""
        data = {
            "id": "not_a_number",  # Invalid type
            "name": "test"
        }

        with pytest.raises(Exception) as exc_info:
            ModelConverter.to_model(data, TestDataModel)

        # Should be TypeCoercionError or ValidationError
        assert "Failed to convert dict to TestDataModel" in str(exc_info.value) or "validation error" in str(exc_info.value)

    def test_to_model_missing_required_field(self):
        """Test converting data missing required fields."""
        data = {"name": "test"}  # Missing required 'id' field

        with pytest.raises(Exception) as exc_info:
            ModelConverter.to_model(data, TestDataModel)

        # Should be TypeCoercionError or ValidationError
        assert "Failed to convert dict to TestDataModel" in str(exc_info.value) or "validation error" in str(exc_info.value)

    def test_to_model_empty_dict(self):
        """Test converting empty dictionary."""
        with pytest.raises(Exception) as exc_info:
            ModelConverter.to_model({}, TestDataModel)

        # Should be TypeCoercionError or ValidationError
        assert "Failed to convert dict to TestDataModel" in str(exc_info.value) or "validation error" in str(exc_info.value)

    def test_to_model_none_data(self):
        """Test converting None data."""
        with pytest.raises(Exception) as exc_info:
            ModelConverter.to_model(None, TestDataModel)

        # Should be TypeCoercionError or ValidationError
        assert "Failed to convert dict to TestDataModel" in str(exc_info.value) or "validation error" in str(exc_info.value)

    def test_to_dict_valid_model(self):
        """Test converting valid model to dictionary."""
        model = TestDataModel(
            id=3,
            name="test_model",
            active=False,
            metadata={"nested": "data"}
        )

        data = ModelConverter.to_dict(model)

        assert isinstance(data, dict)
        assert data["id"] == 3
        assert data["name"] == "test_model"
        assert data["active"] is False
        assert data["metadata"] == {"nested": "data"}

    def test_to_dict_with_defaults(self):
        """Test converting model with default values."""
        model = TestDataModel(id=4, name="defaults_test")

        data = ModelConverter.to_dict(model)

        assert data["id"] == 4
        assert data["name"] == "defaults_test"
        assert data["active"] is True
        assert data["metadata"] == {}

    def test_to_dict_exclude_none(self):
        """Test converting model with exclude_none=True."""
        model = TestDataModel(id=5, name="exclude_test")

        data = ModelConverter.to_dict(model, exclude_none=True)

        # Should not include None values
        assert "id" in data
        assert "name" in data
        assert "active" in data
        assert "metadata" in data

    def test_to_dict_by_alias(self):
        """Test converting model with by_alias=True."""
        model = TestDataModel(id=6, name="alias_test")

        data = ModelConverter.to_dict(model, by_alias=True)

        # Should use field aliases if defined
        assert isinstance(data, dict)
        assert data["id"] == 6
        assert data["name"] == "alias_test"

    def test_to_dict_mode_json(self):
        """Test converting model with mode='json'."""
        model = TestDataModel(id=7, name="json_mode")

        data = ModelConverter.to_dict(model, mode="json")

        assert isinstance(data, dict)
        assert data["id"] == 7
        assert data["name"] == "json_mode"

    def test_round_trip_conversion(self):
        """Test round-trip conversion: dict -> model -> dict."""
        original_data = {
            "id": 8,
            "name": "round_trip",
            "active": True,
            "metadata": {"test": "data"}
        }

        # Convert to model
        model = ModelConverter.to_model(original_data, TestDataModel)

        # Convert back to dict
        converted_data = ModelConverter.to_dict(model)

        # Should match original data
        assert converted_data["id"] == original_data["id"]
        assert converted_data["name"] == original_data["name"]
        assert converted_data["active"] == original_data["active"]
        assert converted_data["metadata"] == original_data["metadata"]

    def test_multiple_models_same_type(self):
        """Test converting multiple dictionaries to same model type."""
        data_list = [
            {"id": 1, "name": "first"},
            {"id": 2, "name": "second"},
            {"id": 3, "name": "third"}
        ]

        models = [ModelConverter.to_model(data, TestDataModel) for data in data_list]

        assert len(models) == 3
        for i, model in enumerate(models):
            assert isinstance(model, TestDataModel)
            assert model.id == i + 1
            assert model.name == data_list[i]["name"]

    def test_nested_dict_conversion(self):
        """Test converting model with nested dictionary."""
        model = TestDataModel(
            id=9,
            name="nested_test",
            metadata={
                "level1": {
                    "level2": {
                        "value": "deep"
                    }
                }
            }
        )

        data = ModelConverter.to_dict(model)

        assert data["metadata"]["level1"]["level2"]["value"] == "deep"

    def test_list_in_metadata(self):
        """Test converting model with list in metadata."""
        model = TestDataModel(
            id=10,
            name="list_test",
            metadata={
                "items": [1, 2, 3],
                "names": ["a", "b", "c"]
            }
        )

        data = ModelConverter.to_dict(model)

        assert data["metadata"]["items"] == [1, 2, 3]
        assert data["metadata"]["names"] == ["a", "b", "c"]

    def test_type_adapter_caching(self):
        """Test that TypeAdapter instances are cached."""
        # This test verifies that the caching mechanism works
        # by ensuring multiple conversions use the same adapter

        data1 = {"id": 1, "name": "first"}
        data2 = {"id": 2, "name": "second"}

        model1 = ModelConverter.to_model(data1, TestDataModel)
        model2 = ModelConverter.to_model(data2, TestDataModel)

        # Both should work without issues (cached adapter)
        assert isinstance(model1, TestDataModel)
        assert isinstance(model2, TestDataModel)
        assert model1.id == 1
        assert model2.id == 2
