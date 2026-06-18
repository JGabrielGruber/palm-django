from __future__ import annotations

import pytest
from palm.core import DictStateSchema

from palm_django import get_app
from palm_django.providers.provider import DjangoModelProvider
from palm_django.resources.config import PalmResourceConfig
from palm_django.resources.registry import build_resource_definitions, get_palm_resource_config
from palm_django.resources.schema import (
    build_action_input_schema,
    model_data_schema_name,
    model_fields_schema_dict,
    model_to_dict_state_schema,
    schema_enabled,
    validate_model_data,
)
from tests.palm_sample.models import SampleItem, SchemaItem


def test_schema_disabled_by_default() -> None:
    config = get_palm_resource_config(SampleItem)
    assert config is not None
    assert schema_enabled(config) is False
    assert build_action_input_schema(SampleItem, "create", config) is None


def test_schema_item_config_enabled() -> None:
    config = get_palm_resource_config(SchemaItem)
    assert config is not None
    assert schema_enabled(config) is True


def test_model_fields_schema_dict_maps_char_and_integer() -> None:
    config = get_palm_resource_config(SchemaItem)
    assert config is not None
    schema = model_fields_schema_dict(
        SchemaItem,
        config,
        writable_only=True,
        for_create=True,
    )
    assert schema["type"] == "object"
    assert schema["properties"]["name"]["type"] == "string"
    assert schema["properties"]["name"]["maxLength"] == 80
    assert schema["properties"]["quantity"]["type"] == "integer"
    assert "name" in schema["required"]
    assert "quantity" not in schema["required"]


def test_dict_state_schema_validates_model_data() -> None:
    config = get_palm_resource_config(SchemaItem)
    assert config is not None
    schema = model_to_dict_state_schema(SchemaItem, config, writable_only=True)
    assert schema.validate_state({"name": "Valid", "quantity": 2}) == []
    errors = schema.validate_state({"quantity": 1})
    assert errors == ["missing required key: name"]


def test_create_resource_definition_has_input_and_output_schema() -> None:
    config = get_palm_resource_config(SchemaItem)
    assert config is not None
    definitions = build_resource_definitions(SchemaItem, config)
    create = next(item for item in definitions if item.action == "create")
    assert create.input_schema is not None
    assert create.input_schema["properties"]["data"]["type"] == "object"
    assert create.output_schema is not None
    assert create.output_schema["properties"]["name"]["type"] == "string"
    assert create.metadata["data_schema_ref"] == model_data_schema_name(SchemaItem, config)


@pytest.mark.django_db
def test_state_schema_definitions_registered() -> None:
    app = get_app()
    names = {schema.name for schema in app.repository().list_schemas()}
    assert "palm_sample.schemaitem.data" in names
    assert "palm_sample.schemaitem.instance" in names


@pytest.mark.django_db
def test_provider_validates_create_payload_when_schema_enabled() -> None:
    provider = DjangoModelProvider()
    provider.connect()
    result = provider.invoke(
        "create",
        params={
            "model": "palm_sample.SchemaItem",
            "data": {"quantity": 3},
        },
    )
    assert result.success is False
    assert "name" in (result.error or "")
    provider.disconnect()


@pytest.mark.django_db
def test_provider_accepts_valid_create_payload() -> None:
    provider = DjangoModelProvider()
    provider.connect()
    result = provider.invoke(
        "create",
        params={
            "model": "palm_sample.SchemaItem",
            "data": {"name": "Schema Widget", "quantity": 4},
        },
    )
    assert result.success is True
    assert result.data["name"] == "Schema Widget"
    provider.disconnect()


def test_validate_model_data_rejects_wrong_type() -> None:
    config = PalmResourceConfig(schema=True)
    errors = validate_model_data(SchemaItem, {"name": "x", "quantity": "bad"}, config)
    assert any("quantity" in item for item in errors)


def test_palm_resource_inner_class_enables_schema() -> None:
    from django.db import models

    class MetaModel(models.Model):
        class PalmResource:
            actions = ["create"]
            schema = True

        title = models.CharField(max_length=20)

        class Meta:
            app_label = "palm_sample"

    config = get_palm_resource_config(MetaModel)
    assert config is not None
    assert schema_enabled(config) is True


def test_dict_state_schema_accepts_integer_quantity() -> None:
    config = PalmResourceConfig(schema=True)
    schema = DictStateSchema(
        model_fields_schema_dict(SchemaItem, config, writable_only=True, for_create=True)
    )
    assert schema.validate_state({"name": "Item", "quantity": 5}) == []