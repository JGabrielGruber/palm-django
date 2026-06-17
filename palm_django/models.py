"""
Django ORM models for Palm Engine persistence.
"""

from __future__ import annotations

from django.db import models


class PalmDefinition(models.Model):
    """Flow, process, resource, and state-schema definition records."""

    class Kind(models.TextChoices):
        FLOW = "flow", "Flow"
        PROCESS = "process", "Process"
        RESOURCE = "resource", "Resource"
        STATE_SCHEMA = "state_schema", "State schema"

    kind = models.CharField(max_length=32, choices=Kind.choices, db_index=True)
    definition_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255, blank=True, default="")
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "definition_id"],
                name="palm_django_definition_kind_id_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["kind", "name"], name="palm_django_def_kind_name_idx"),
        ]
        verbose_name = "Palm definition"
        verbose_name_plural = "Palm definitions"

    def __str__(self) -> str:
        return f"{self.kind}:{self.definition_id}"


class PalmProcessInstance(models.Model):
    """Durable process instance with embedded snapshots and status history."""

    instance_id = models.CharField(max_length=255, primary_key=True)
    job_id = models.CharField(max_length=255, db_index=True)
    status = models.CharField(max_length=64, db_index=True)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "updated_at"], name="palm_django_inst_status_idx"),
        ]
        verbose_name = "Palm process instance"
        verbose_name_plural = "Palm process instances"

    def __str__(self) -> str:
        return self.instance_id


class PalmStorageEntry(models.Model):
    """Generic key-value storage for indexes, projections, outbox, and other Palm keys."""

    key = models.CharField(max_length=512, primary_key=True)
    namespace = models.CharField(max_length=64, db_index=True)
    value = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["namespace", "updated_at"], name="palm_django_kv_ns_idx"),
        ]
        verbose_name = "Palm storage entry"
        verbose_name_plural = "Palm storage entries"

    def __str__(self) -> str:
        return self.key