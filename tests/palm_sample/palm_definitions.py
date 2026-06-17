"""
Sample Palm definitions for palm-django integration tests.

Includes a runnable DAG flow and a wizard that creates a ``SampleItem`` via
Django model resources — mirroring Palm's ``resource_customer_wizard`` pattern.
"""

from __future__ import annotations

from palm.common.persistence.definition_repository import DefinitionRepository
from palm.definitions.flow import FlowDefinition

ITEM_WIZARD_FLOW = FlowDefinition(
    id="flow-item-wizard",
    name="item_wizard",
    pattern="wizard",
    options={
        "include_summary": True,
        "allow_backtrack": True,
        "steps": [
            {
                "slug": "item_name",
                "title": "Item name",
                "prompt": "Enter the inventory item name",
                "validation": [{"rule": "not_empty"}],
            },
            {
                "slug": "quantity",
                "title": "Quantity",
                "prompt": "How many units?",
                "validation": [{"rule": "not_empty"}],
            },
            {
                "slug": "create-item",
                "title": "Create item",
                "step_kind": "resource",
                "resource_ref": "palm_sample.sampleitem.create",
                "action": "create",
                "params": {
                    "data": {
                        "name": "{{ state.item_name }}",
                        "quantity": "{{ state.quantity }}",
                    }
                },
                "output_key": "sampleitem",
            },
            {
                "slug": "verify-item",
                "title": "Verify item",
                "step_kind": "resource",
                "resource_ref": "palm_sample.sampleitem.get",
                "action": "get",
                "params": {"pk": "{{ state.sampleitem.id }}"},
                "output_key": "verified_item",
            },
        ],
    },
)


def register_definitions(repository: DefinitionRepository) -> None:
    repository.register_flow(
        FlowDefinition(
            id="sample_flow",
            name="sample_flow",
            pattern="dag",
            options={"name": "sample_flow"},
        )
    )
    repository.register_flow(ITEM_WIZARD_FLOW)