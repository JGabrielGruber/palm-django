from __future__ import annotations

import pytest
from palm.common.persistence.definition_repository import DefinitionRepository
from palm.common.persistence.instance_repository import InstanceRepository
from palm.core.storage import StorageEngine
from palm.definitions.flow import FlowDefinition
from palm.instances.process_instance import ProcessInstance

from palm_django.backends import storage_health_report
from palm_django.models import PalmDefinition, PalmProcessInstance, PalmStorageEntry
from palm_django.settings import build_palm_settings_dict
from palm_django.storages import register_django_storage


@pytest.fixture
def django_storage_engine() -> StorageEngine:
    register_django_storage()
    engine = StorageEngine()
    engine.initialize(backend="django")
    yield engine
    engine.shutdown()


@pytest.mark.django_db
def test_default_storage_backend_is_django() -> None:
    assert build_palm_settings_dict()["storage_backend"] == "django"


@pytest.mark.django_db
def test_storage_backend_roundtrip_definition(django_storage_engine: StorageEngine) -> None:
    repository = DefinitionRepository(django_storage_engine)
    flow = FlowDefinition(id="persist_flow", name="persist_flow", pattern="sequence")
    repository.save_flow(flow)

    reloaded = DefinitionRepository(django_storage_engine)
    loaded = reloaded.get_flow_by_id("persist_flow")
    assert loaded.name == "persist_flow"
    assert PalmDefinition.objects.filter(kind="flow", definition_id="persist_flow").exists()
    assert PalmStorageEntry.objects.filter(key="palm:definitions:index:flow").exists()


@pytest.mark.django_db
def test_storage_backend_roundtrip_instance(django_storage_engine: StorageEngine) -> None:
    repository = InstanceRepository(django_storage_engine)
    instance = ProcessInstance(
        instance_id="inst-roundtrip",
        job_id="job-roundtrip",
        status="RUNNING",
        state_snapshot={"step": 1},
        flow_definition={"name": "demo", "pattern": "sequence"},
        pattern="sequence",
        flow_id="demo",
        flow_name="demo",
    )
    repository.save(instance)

    reloaded = InstanceRepository(django_storage_engine)
    loaded = reloaded.get("inst-roundtrip")
    assert loaded.job_id == "job-roundtrip"
    assert loaded.state_snapshot == {"step": 1}
    assert PalmProcessInstance.objects.filter(instance_id="inst-roundtrip").exists()


@pytest.mark.django_db
def test_storage_backend_kv_entries(django_storage_engine: StorageEngine) -> None:
    django_storage_engine.set("palm:projections:instance_index", {"entries": {}, "updated_at": 1})
    value = django_storage_engine.get("palm:projections:instance_index")
    assert value == {"entries": {}, "updated_at": 1}
    assert PalmStorageEntry.objects.filter(key="palm:projections:instance_index").exists()


@pytest.mark.django_db
def test_storage_health_report_ready() -> None:
    report = storage_health_report()
    assert report["tables_ready"] is True
    assert report["missing_tables"] == []


@pytest.mark.django_db
def test_storage_delete_is_idempotent(django_storage_engine: StorageEngine) -> None:
    django_storage_engine.set("palm:projections:wizard_progress", {"entries": {}})
    django_storage_engine.delete("palm:projections:wizard_progress")
    django_storage_engine.delete("palm:projections:wizard_progress")
    assert django_storage_engine.get("palm:projections:wizard_progress") is None