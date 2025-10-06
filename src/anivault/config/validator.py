"""
Configuration Validator for AniVault

This module provides the ConfigValidator class for validating configuration
data and providing detailed error messages.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from anivault.config.validation import TomlConfig
from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Handles configuration validation and error reporting."""

    @staticmethod
    def validate_config_dict(config_dict: dict[str, Any]) -> list[str]:
        """Validate configuration dictionary.

        Args:
            config_dict: Configuration dictionary to validate

        Returns:
            List of validation error messages. Empty list if valid.
        """
        try:
            # Validate using Pydantic model
            TomlConfig.model_validate(config_dict)
            logger.debug("Configuration validation successful")
            return []

        except ValidationError as e:
            errors = []
            for error in e.errors():
                field_path = " -> ".join(str(loc) for loc in error["loc"])
                errors.append(f"{field_path}: {error['msg']}")
            logger.warning("Configuration validation failed with %d errors", len(errors))
            return errors
        except Exception as e:
            error_msg = f"Unexpected validation error: {e}"
            logger.exception("Unexpected validation error")
            return [error_msg]

    @staticmethod
    def validate_config_object(config: TomlConfig) -> list[str]:
        """Validate configuration object.

        Args:
            config: TomlConfig object to validate

        Returns:
            List of validation error messages. Empty list if valid.
        """
        try:
            # Validate by converting to dict and back
            config_dict = config.model_dump()
            return ConfigValidator.validate_config_dict(config_dict)
        except Exception as e:
            error_msg = f"Failed to validate config object: {e}"
            logger.exception("Failed to validate config object")
            return [error_msg]

    @staticmethod
    def validate_field_value(section: str, field: str, value: Any) -> list[str]:
        """Validate a specific field value.

        Args:
            section: Configuration section name
            field: Field name within the section
            value: Value to validate

        Returns:
            List of validation error messages. Empty list if valid.
        """
        try:
            # Create a minimal config dict with just this field
            config_dict = {section: {field: value}}

            # Validate using the full schema
            TomlConfig.model_validate(config_dict)
            logger.debug("Field validation successful: %s.%s", section, field)
            return []

        except ValidationError as e:
            errors = []
            for error in e.errors():
                field_path = " -> ".join(str(loc) for loc in error["loc"])
                errors.append(f"{field_path}: {error['msg']}")
            logger.warning("Field validation failed for %s.%s", section, field)
            return errors
        except Exception as e:
            error_msg = f"Failed to validate field {section}.{field}: {e}"
            logger.exception("Failed to validate field")
            return [error_msg]

    @staticmethod
    def get_config_schema() -> dict[str, Any]:
        """Get the configuration schema.

        Returns:
            JSON schema for the configuration
        """
        try:
            schema = TomlConfig.model_json_schema()
            logger.debug("Retrieved configuration schema")
            return schema
        except Exception as e:
            logger.exception("Failed to get configuration schema")
            raise ApplicationError(
                ErrorCode.CONFIG_ERROR,
                f"Failed to get configuration schema: {e}",
                ErrorContext(operation="get_config_schema"),
            ) from e

    @staticmethod
    def get_field_description(section: str, field: str) -> str | None:
        """Get description for a specific configuration field.

        Args:
            section: Configuration section name
            field: Field name within the section

        Returns:
            Field description if found, None otherwise
        """
        try:
            schema = ConfigValidator.get_config_schema()
            properties = schema.get("properties", {})
            section_schema = properties.get(section, {})
            field_schema = section_schema.get("properties", {}).get(field, {})
            return field_schema.get("description")
        except (KeyError, TypeError, AttributeError) as e:
            logger.warning("Failed to get field description for %s.%s: %s", section, field, e)
            return None

    @staticmethod
    def get_required_fields(section: str) -> list[str]:
        """Get list of required fields for a configuration section.

        Args:
            section: Configuration section name

        Returns:
            List of required field names
        """
        try:
            schema = ConfigValidator.get_config_schema()
            properties = schema.get("properties", {})
            section_schema = properties.get(section, {})
            required = section_schema.get("required", [])
            logger.debug("Retrieved %d required fields for section %s", len(required), section)
            return required
        except (KeyError, TypeError, AttributeError) as e:
            logger.warning("Failed to get required fields for section %s: %s", section, e)
            return []
