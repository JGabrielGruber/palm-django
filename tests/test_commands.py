from __future__ import annotations

import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from tests.palm_sample.models import SampleItem


@pytest.mark.django_db
def test_palm_flow_list_shows_sample_flow() -> None:
    out = StringIO()
    call_command("palm", "flow", "list", stdout=out)
    assert "sample_flow" in out.getvalue()


@pytest.mark.django_db
def test_palm_flow_start_submits_job() -> None:
    out = StringIO()
    call_command("palm", "flow", "start", "sample_flow", stdout=out)
    output = out.getvalue()
    assert "Flow submitted" in output
    assert "job_id:" in output


@pytest.mark.django_db
def test_palm_run_auto_resolves_flow() -> None:
    out = StringIO()
    call_command("palm", "run", "sample_flow", stdout=out)
    assert "Flow submitted" in out.getvalue()


@pytest.mark.django_db
def test_palm_resource_list_includes_model_resources() -> None:
    out = StringIO()
    call_command("palm", "resource", "list", stdout=out)
    output = out.getvalue()
    assert "palm_sample.sampleitem.create" in output


@pytest.mark.django_db
def test_palm_resource_invoke_create() -> None:
    out = StringIO()
    call_command(
        "palm",
        "resource",
        "invoke",
        "palm_sample.sampleitem.create",
        "--state",
        json.dumps({"data": {"name": "CLI Item", "quantity": 4}}),
        stdout=out,
    )
    output = out.getvalue()
    assert "Resource invoked successfully" in output
    assert SampleItem.objects.filter(name="CLI Item").exists()


@pytest.mark.django_db
def test_palm_instance_list_runs() -> None:
    out = StringIO()
    call_command("palm", "instance", "list", stdout=out)
    assert "Instances" in out.getvalue()


@pytest.mark.django_db
def test_palm_doctor_lists_operator_tools() -> None:
    out = StringIO()
    call_command("palm", "doctor", stdout=out)
    output = out.getvalue()
    assert "[Operator Tools]" in output
    assert "doctor, run, flow, instance, resource" in output


@pytest.mark.django_db
def test_palm_run_unknown_ref_raises() -> None:
    with pytest.raises(CommandError, match="Unknown flow or process"):
        call_command("palm", "run", "does-not-exist")