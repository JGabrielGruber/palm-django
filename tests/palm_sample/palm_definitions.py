"""Sample Palm definitions module for discovery tests."""

from palm.common.persistence.definition_repository import DefinitionRepository
from palm.definitions.flow import FlowDefinition


def register_definitions(repository: DefinitionRepository) -> None:
    repository.register_flow(
        FlowDefinition(
            id="sample_flow",
            name="sample_flow",
            pattern="sequence",
        )
    )