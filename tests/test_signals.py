from __future__ import annotations

import pytest

from palm_django import get_app
from palm_django.providers.provider import DjangoModelProvider
from palm_django.signals import palm_model_saved, palm_resource_invoked
from tests.palm_sample.models import SampleItem


@pytest.mark.django_db
def test_palm_resource_invoked_on_provider_success() -> None:
    events: list[tuple[str, str]] = []

    def on_invoked(**kwargs):
        events.append((kwargs["provider"], kwargs["action"]))

    palm_resource_invoked.connect(on_invoked, weak=False)
    try:
        provider = DjangoModelProvider()
        provider.connect()
        result = provider.invoke(
            "create",
            params={
                "model": "palm_sample.SampleItem",
                "data": {"name": "Signal Item", "quantity": 1},
            },
        )
        assert result.success is True
        assert ("django_model", "create") in events
        provider.disconnect()
    finally:
        palm_resource_invoked.disconnect(on_invoked)


@pytest.mark.django_db
def test_palm_model_saved_on_direct_orm_save() -> None:
    saved: list[tuple[str, bool]] = []

    def on_saved(**kwargs):
        saved.append((kwargs["model_label"], kwargs["created"]))

    palm_model_saved.connect(on_saved, weak=False)
    try:
        SampleItem.objects.create(name="ORM Save", quantity=1)
        assert ("palm_sample.SampleItem", True) in saved
    finally:
        palm_model_saved.disconnect(on_saved)


@pytest.mark.django_db
def test_palm_model_saved_suppressed_during_provider_mutation() -> None:
    saved: list[str] = []

    def on_saved(**kwargs):
        saved.append(kwargs["model_label"])

    palm_model_saved.connect(on_saved, weak=False)
    try:
        app = get_app()
        result = app.invoke_resource(
            "palm_sample.sampleitem.create",
            state={"data": {"name": "Provider Save", "quantity": 2}},
        )
        assert result.success is True
        assert saved == []
    finally:
        palm_model_saved.disconnect(on_saved)