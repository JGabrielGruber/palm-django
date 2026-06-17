from __future__ import annotations

import pytest
from django.db import transaction

from palm_django import get_app
from palm_django.backends import DjangoStorageBackend
from palm_django.models import PalmStorageEntry
from palm_django.providers.provider import DjangoModelProvider
from palm_django.transactions import palm_atomic
from tests.palm_sample.models import SampleItem


@pytest.mark.django_db
def test_django_atomic_joins_outer_block_on_rollback() -> None:
    backend = DjangoStorageBackend()
    backend.open()
    key = "palm:projections:tx_test"

    with pytest.raises(RuntimeError):
        with transaction.atomic():
            backend.set(key, {"rolled": True})
            raise RuntimeError("rollback outer")

    assert backend.get(key) is None
    backend.close()


@pytest.mark.django_db
def test_palm_atomic_rolls_back_model_and_storage_together() -> None:
    backend = DjangoStorageBackend()
    backend.open()
    key = "palm:projections:combo_tx"

    with pytest.raises(ValueError):
        with palm_atomic():
            SampleItem.objects.create(name="Rollback Me", quantity=1)
            backend.set(key, {"combo": True})
            raise ValueError("abort")

    assert not SampleItem.objects.filter(name="Rollback Me").exists()
    assert backend.get(key) is None
    backend.close()


@pytest.mark.django_db
def test_provider_create_inside_outer_atomic_rolls_back() -> None:
    provider = DjangoModelProvider()
    provider.connect()

    with pytest.raises(RuntimeError):
        with transaction.atomic():
            result = provider.invoke(
                "create",
                params={
                    "model": "palm_sample.SampleItem",
                    "data": {"name": "Nested TX", "quantity": 3},
                },
            )
            assert result.success is True
            raise RuntimeError("rollback provider create")

    assert not SampleItem.objects.filter(name="Nested TX").exists()
    provider.disconnect()


@pytest.mark.django_db
def test_storage_set_inside_palm_atomic_commits_with_django() -> None:
    backend = DjangoStorageBackend()
    backend.open()
    key = "palm:projections:combo_commit"

    with palm_atomic():
        SampleItem.objects.create(name="Committed", quantity=2)
        backend.set(key, {"combo": True})

    assert SampleItem.objects.filter(name="Committed").exists()
    assert backend.get(key) == {"combo": True}
    assert PalmStorageEntry.objects.filter(key=key).exists()
    backend.close()


@pytest.mark.django_db
def test_resource_invoke_inside_atomic_rolls_back_on_failure() -> None:
    app = get_app()

    with pytest.raises(RuntimeError):
        with transaction.atomic():
            result = app.invoke_resource(
                "palm_sample.sampleitem.create",
                state={"data": {"name": "Atomic Item", "quantity": 1}},
            )
            assert result.success is True
            raise RuntimeError("rollback invoke")

    assert not SampleItem.objects.filter(name="Atomic Item").exists()