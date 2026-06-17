from __future__ import annotations

import pytest
from palm.common.patterns.build_context import PatternBuildContext
from palm.common.patterns.builder import build_pattern
from palm.core.behavior_tree import PatternStatus
from palm.patterns.wizard.keys import WizardKeys
from palm.patterns.wizard.pattern import WizardPattern
from palm.states import BlackboardState

from palm_django import get_app
from tests.palm_sample.models import SampleItem


@pytest.mark.django_db
def test_item_wizard_flow_is_registered() -> None:
    app = get_app()
    names = {flow.name for flow in app.list_flows()}
    assert "item_wizard" in names


@pytest.mark.django_db
def test_item_wizard_resource_steps_create_and_verify_item() -> None:
    app = get_app()
    flow = next(item for item in app.list_flows() if item.name == "item_wizard")
    assert flow.pattern == "wizard"

    wizard = build_pattern(
        flow,
        context=PatternBuildContext(resource_engine=app.runtime().resource),
    )
    assert isinstance(wizard, WizardPattern)
    state = BlackboardState()

    assert wizard.tick(state) == PatternStatus.WAITING_FOR_INPUT
    wizard.provide_input(state, "Gizmo")
    assert wizard.tick(state) == PatternStatus.WAITING_FOR_INPUT
    wizard.provide_input(state, "7")
    assert wizard.tick(state) == PatternStatus.WAITING_FOR_INPUT
    wizard.provide_input(state, True)
    assert wizard.tick(state) == PatternStatus.SUCCESS

    answers = state.get(WizardKeys.ANSWERS)
    assert answers["item_name"] == "Gizmo"
    assert answers["quantity"] == "7"
    assert answers["sampleitem"]["name"] == "Gizmo"
    assert answers["verified_item"]["name"] == "Gizmo"
    assert answers["verified_item"]["quantity"] == 7
    assert SampleItem.objects.filter(name="Gizmo", quantity=7).exists()