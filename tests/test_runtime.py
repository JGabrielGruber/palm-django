from __future__ import annotations

import pytest

from palm_django import get_app, get_host, is_palm_started


@pytest.mark.django_db
def test_appconfig_bootstraps_host() -> None:
    assert is_palm_started()
    host = get_host()
    app = get_app()
    assert host.is_started
    assert app.is_runtime_started()


@pytest.mark.django_db
def test_discovery_registers_sample_flow() -> None:
    app = get_app()
    flow_names = {flow.name for flow in app.list_flows()}
    assert "sample_flow" in flow_names