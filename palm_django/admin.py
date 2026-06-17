"""
Django Admin integration for Palm persistence models.
"""

from __future__ import annotations

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest

from palm_django.models import PalmDefinition, PalmProcessInstance, PalmStorageEntry
from palm_django.runtime import bootstrap_palm, get_host, is_palm_started


def _ensure_host(request: HttpRequest) -> bool:
    if not is_palm_started():
        bootstrap_palm()
    if not is_palm_started():
        messages.error(
            request,
            "Palm ApplicationHost is not started. Run migrations and `manage.py palm doctor`.",
        )
        return False
    return True


class PalmDefinitionAdmin(admin.ModelAdmin):
    list_display = ("kind", "definition_id", "name", "updated_at")
    list_filter = ("kind",)
    search_fields = ("definition_id", "name")
    readonly_fields = ("created_at", "updated_at")
    actions = ("start_flow",)

    @admin.action(description="Start flow (flow definitions only)")
    def start_flow(self, request: HttpRequest, queryset: QuerySet[PalmDefinition]) -> None:
        if not _ensure_host(request):
            return

        started = 0
        host = get_host()
        for row in queryset:
            if row.kind != PalmDefinition.Kind.FLOW:
                messages.warning(request, f"Skipped {row}: not a flow definition.")
                continue
            flow_name = row.name or row.definition_id
            try:
                job = host.submit_flow(flow_name)
            except Exception as exc:
                messages.error(request, f"Failed to start {flow_name}: {exc}")
                continue
            started += 1
            messages.success(
                request,
                f"Started flow {flow_name} (job={job.id}, status={job.status.value})",
            )
        if started:
            messages.info(request, f"Started {started} flow(s).")


class PalmProcessInstanceAdmin(admin.ModelAdmin):
    list_display = ("instance_id", "job_id", "status", "updated_at")
    list_filter = ("status",)
    search_fields = ("instance_id", "job_id")
    readonly_fields = ("created_at", "updated_at")
    actions = ("resume_instance",)

    @admin.action(description="Resume selected instances")
    def resume_instance(
        self,
        request: HttpRequest,
        queryset: QuerySet[PalmProcessInstance],
    ) -> None:
        if not _ensure_host(request):
            return

        host = get_host()
        resumed = 0
        for row in queryset:
            try:
                job = host.resume_process(row.instance_id)
            except Exception as exc:
                messages.error(request, f"Failed to resume {row.instance_id}: {exc}")
                continue
            resumed += 1
            messages.success(
                request,
                f"Resumed {row.instance_id} (job={job.id}, status={job.status.value})",
            )
        if resumed:
            messages.info(request, f"Resumed {resumed} instance(s).")


class PalmStorageEntryAdmin(admin.ModelAdmin):
    list_display = ("key", "namespace", "updated_at")
    list_filter = ("namespace",)
    search_fields = ("key",)
    readonly_fields = ("updated_at",)


def register_admin_models() -> None:
    """Register Palm models when ``django.contrib.admin`` is installed."""
    from django.apps import apps

    if not apps.is_installed("django.contrib.admin"):
        return

    for model, model_admin in (
        (PalmDefinition, PalmDefinitionAdmin),
        (PalmProcessInstance, PalmProcessInstanceAdmin),
        (PalmStorageEntry, PalmStorageEntryAdmin),
    ):
        if model not in admin.site._registry:
            admin.site.register(model, model_admin)