from __future__ import annotations

import pytest
from django.test import override_settings

from palm_django.settings import build_palm_settings_dict, get_django_integration_settings


@pytest.mark.django_db
def test_build_palm_settings_uses_defaults() -> None:
    config = build_palm_settings_dict()
    assert config["load_example_definitions"] is False
    assert config["storage_backend"] == "django"


@override_settings(
    PALM={"STORAGE_BACKEND": "filesystem", "DATA_DIR": "/tmp/palm-data"},
    PALM_ENABLE_STATE_SNAPSHOT=True,
)
@pytest.mark.django_db
def test_build_palm_settings_merges_dict_and_prefixed() -> None:
    config = build_palm_settings_dict()
    assert config["storage_backend"] == "filesystem"
    assert str(config["data_dir"]) == "/tmp/palm-data"
    assert config["enable_state_snapshot"] is True


@override_settings(PALM={"AUTO_START": False, "DISCOVERY_MODULES": ["palm"]})
@pytest.mark.django_db
def test_django_integration_settings() -> None:
    integration = get_django_integration_settings()
    assert integration["auto_start"] is False
    assert integration["discovery_modules"] == ("palm",)