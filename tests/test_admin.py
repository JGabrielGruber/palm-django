from __future__ import annotations

import pytest
from django.contrib import admin
from django.test import override_settings

from palm_django.models import PalmDefinition, PalmProcessInstance, PalmStorageEntry


@pytest.mark.django_db
def test_admin_module_defines_model_admins() -> None:
    import palm_django.admin as palm_admin

    assert hasattr(palm_admin, "PalmDefinitionAdmin")
    assert hasattr(palm_admin, "PalmProcessInstanceAdmin")
    assert hasattr(palm_admin, "PalmStorageEntryAdmin")
    assert callable(palm_admin.register_admin_models)


@override_settings(
    INSTALLED_APPS=[
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "palm_django",
        "tests.palm_sample",
    ]
)
@pytest.mark.django_db
def test_admin_registers_palm_models() -> None:
    from palm_django.admin import register_admin_models

    register_admin_models()

    assert PalmDefinition in admin.site._registry
    assert PalmProcessInstance in admin.site._registry
    assert PalmStorageEntry in admin.site._registry