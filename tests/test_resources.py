from __future__ import annotations

import pytest
from palm.core.resource import bind_resource_params

from palm_django import get_app
from palm_django.providers.provider import DjangoModelProvider
from palm_django.resources.registry import PROVIDER_NAME, list_registered_models
from tests.palm_sample.models import SampleItem


@pytest.mark.django_db
def test_decorated_models_are_discovered() -> None:
    labels = {label for label, _ in list_registered_models()}
    assert "palm_sample.SampleItem" in labels
    assert "palm_sample.ManualResourceItem" in labels


@pytest.mark.django_db
def test_model_resources_registered_in_repository() -> None:
    app = get_app()
    names = {resource.name for resource in app.list_resources()}
    assert "palm_sample.sampleitem.create" in names
    assert "palm_sample.sampleitem.get" in names
    assert "palm_sample.manualresourceitem.list" in names


@pytest.mark.django_db
def test_provider_create_list_get_roundtrip() -> None:
    provider = DjangoModelProvider()
    provider.connect()

    created = provider.invoke(
        "create",
        params={
            "model": "palm_sample.SampleItem",
            "data": {"name": "Widget", "quantity": 2},
        },
    )
    assert created.success is True
    assert created.data["name"] == "Widget"
    pk = created.data["id"]

    listed = provider.invoke(
        "list",
        params={"model": "palm_sample.SampleItem", "filters": {"name": "Widget"}},
    )
    assert listed.success is True
    assert len(listed.data) == 1

    fetched = provider.invoke(
        "get",
        params={"model": "palm_sample.SampleItem", "pk": pk},
    )
    assert fetched.success is True
    assert fetched.data["quantity"] == 2
    provider.disconnect()


@pytest.mark.django_db
def test_invoke_via_resource_definition_with_state_binding() -> None:
    app = get_app()
    result = app.invoke_resource(
        "palm_sample.sampleitem.create",
        state={"data": {"name": "Bound", "quantity": 5}},
    )
    assert result.success is True
    pk = result.data["id"]

    bound = bind_resource_params(
        app.resolve_resource("palm_sample.sampleitem.get").params,
        {"pk": pk},
    )
    fetched = app.invoke_resource(
        "palm_sample.sampleitem.get",
        params=bound,
    )
    assert fetched.success is True
    assert fetched.data["name"] == "Bound"
    assert SampleItem.objects.filter(pk=pk).exists()


@pytest.mark.django_db
def test_invoke_update_and_delete() -> None:
    item = SampleItem.objects.create(name="Temp", quantity=1)
    app = get_app()

    updated = app.invoke_resource(
        "palm_sample.sampleitem.update",
        state={"pk": item.pk, "data": {"quantity": 9}},
    )
    assert updated.success is True
    assert updated.data["quantity"] == 9

    deleted = app.invoke_resource(
        "palm_sample.sampleitem.delete",
        state={"pk": item.pk},
    )
    assert deleted.success is True
    assert not SampleItem.objects.filter(pk=item.pk).exists()


@pytest.mark.django_db
def test_direct_provider_invoke_from_app() -> None:
    app = get_app()
    result = app.invoke_resource(
        provider=PROVIDER_NAME,
        action="list",
        params={"model": "palm_sample.SampleItem"},
    )
    assert result.success is True
    assert isinstance(result.data, list)