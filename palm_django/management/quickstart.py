"""
``palm quickstart`` — scaffold-friendly snippets for new integrations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

MODEL_SNIPPET = '''\
from django.db import models

from palm_django import as_palm_resource


@as_palm_resource(actions=["get", "create", "update", "delete", "list"])
class {model_class}(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.name
'''

DEFINITIONS_SNIPPET = '''\
"""Palm flow definitions for {app_label}."""

from palm.common.persistence.definition_repository import DefinitionRepository
from palm.definitions.flow import FlowDefinition


def register_definitions(repository: DefinitionRepository) -> None:
    repository.register_flow(
        FlowDefinition(
            id="flow-{flow_slug}",
            name="{flow_name}",
            pattern="wizard",
            options={{
                "include_summary": True,
                "steps": [
                    {{
                        "slug": "name",
                        "title": "Name",
                        "prompt": "Enter a name",
                        "validation": [{{"rule": "not_empty"}}],
                    }},
                    {{
                        "slug": "create-record",
                        "title": "Create record",
                        "step_kind": "resource",
                        "resource_ref": "{resource_prefix}.create",
                        "action": "create",
                        "params": {{"data": {{"name": "{{{{ state.name }}}}"}}}},
                        "output_key": "{output_key}",
                    }},
                ],
            }},
        )
    )
'''


def run_quickstart(command: BaseCommand, options: dict[str, Any]) -> None:
    app_label = (options.get("app") or "").strip()
    write = options.get("write", False)

    if not app_label:
        _print_guide(command)
        return

    try:
        app_config = apps.get_app_config(app_label)
    except LookupError as exc:
        raise CommandError(f"Unknown app {app_label!r}. Check INSTALLED_APPS.") from exc

    model_class = _pascal_case(app_label.rsplit(".", 1)[-1]) + "Item"
    resource_prefix = f"{app_config.label}.{model_class.lower()}"
    flow_name = f"{app_config.label}_onboard"
    flow_slug = flow_name.replace("_", "-")

    command.stdout.write(command.style.MIGRATE_HEADING(f"Quickstart for {app_config.label}"))
    command.stdout.write("")
    command.stdout.write("Add this model to your app's models.py:")
    command.stdout.write("")
    command.stdout.write(MODEL_SNIPPET.format(model_class=model_class))

    definitions_body = DEFINITIONS_SNIPPET.format(
        app_label=app_config.label,
        model_class=model_class,
        resource_prefix=resource_prefix,
        output_key=model_class.lower(),
        flow_name=flow_name,
        flow_slug=flow_slug,
    )

    if write:
        target = Path(app_config.path) / "palm_definitions.py"
        if target.exists():
            raise CommandError(f"{target} already exists. Remove it or omit --write.")
        target.write_text(definitions_body, encoding="utf-8")
        command.stdout.write("")
        command.stdout.write(command.style.SUCCESS(f"Wrote {target}"))
        command.stdout.write("Add the model snippet above to models.py, then run migrate.")
    else:
        command.stdout.write("")
        command.stdout.write(f"Create {app_config.label}/palm_definitions.py:")
        command.stdout.write("")
        command.stdout.write(definitions_body)

    command.stdout.write("")
    command.stdout.write("Next steps:")
    command.stdout.write(f"  1. python manage.py makemigrations {app_config.label}")
    command.stdout.write("  2. python manage.py migrate")
    command.stdout.write(f"  3. python manage.py palm resource list | grep {app_config.label}")
    command.stdout.write(f"  4. python manage.py palm flow start {flow_name}")


def _print_guide(command: BaseCommand) -> None:
    command.stdout.write(command.style.MIGRATE_HEADING("Palm x Django — Quickstart"))
    command.stdout.write("")
    command.stdout.write("  1. Add palm_django to INSTALLED_APPS")
    command.stdout.write("  2. python manage.py migrate palm_django")
    command.stdout.write("  3. Decorate a model with @as_palm_resource")
    command.stdout.write("  4. Add myapp/palm_definitions.py with register_definitions()")
    command.stdout.write("  5. python manage.py palm doctor")
    command.stdout.write("")
    command.stdout.write("Generate snippets for a specific app:")
    command.stdout.write("  python manage.py palm quickstart --app myapp")
    command.stdout.write("  python manage.py palm quickstart --app myapp --write")
    command.stdout.write("")
    command.stdout.write("See tests/palm_sample/ for a full wizard + model resource example.")


def _pascal_case(value: str) -> str:
    return "".join(part.capitalize() for part in value.replace("-", "_").split("_") if part)