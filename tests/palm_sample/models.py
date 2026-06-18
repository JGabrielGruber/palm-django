"""Sample Django models for palm-django integration tests."""

from __future__ import annotations

from django.db import models

from palm_django.resources import as_palm_resource


@as_palm_resource(actions=["get", "create", "update", "delete", "list"])
class SampleItem(models.Model):
    name = models.CharField(max_length=100)
    quantity = models.IntegerField(default=0)

    def __str__(self) -> str:
        return self.name


class ManualResourceItem(models.Model):
    """Registered via class-level ``palm_resource`` instead of the decorator."""

    label = models.CharField(max_length=50)

    palm_resource = {
        "actions": ["get", "list"],
        "output_key": "manual_item",
    }


@as_palm_resource(actions=["create", "get"], schema=True)
class SchemaItem(models.Model):
    """Model with auto-generated Palm schemas for validation."""

    name = models.CharField(max_length=80)
    quantity = models.IntegerField(default=0)