from __future__ import annotations

from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from palm.app.host.roles import HostProfile

from palm_django.management.server import explorer_url, resolve_server_bind


def test_resolve_server_bind_defaults() -> None:
    host, port = resolve_server_bind()
    assert host == "127.0.0.1"
    assert port == 8080


def test_resolve_server_bind_cli_overrides() -> None:
    host, port = resolve_server_bind(host="0.0.0.0", port=9000)
    assert host == "0.0.0.0"
    assert port == 9000


def test_explorer_url() -> None:
    assert explorer_url("127.0.0.1", 8080) == "http://127.0.0.1:8080/explorer"


@pytest.mark.django_db
def test_palm_server_prints_explorer_url() -> None:
    out = StringIO()

    with patch(
        "palm_django.management.server.bootstrap_palm_server",
    ) as bootstrap_mock:
        host = bootstrap_mock.return_value
        host.app.storage.backend_name = "django"
        host.app.list_flows.return_value = [object(), object()]
        host.app.list_resources.return_value = [object()]
        host.run_until_signal = lambda: None

        call_command("palm", "server", "--host", "127.0.0.1", "--port", 8080, stdout=out)

    output = out.getvalue()
    assert "Palm Explorer available at http://127.0.0.1:8080/explorer" in output
    assert "Press Ctrl+C to stop." in output
    assert "Palm server stopped." in output
    bootstrap_mock.assert_called_once_with(host="127.0.0.1", port=8080)


@pytest.mark.django_db
def test_palm_host_server_alias() -> None:
    out = StringIO()

    with patch("palm_django.management.server.bootstrap_palm_server") as bootstrap_mock:
        host = bootstrap_mock.return_value
        host.app.storage.backend_name = "django"
        host.app.list_flows.return_value = []
        host.app.list_resources.return_value = []
        host.run_until_signal = lambda: None

        call_command("palm", "host", "server", "--port", 9090, stdout=out)

    assert "http://127.0.0.1:9090/explorer" in out.getvalue()
    bootstrap_mock.assert_called_once_with(host="127.0.0.1", port=9090)


@pytest.mark.django_db
def test_bootstrap_palm_server_uses_server_profile() -> None:
    from palm_django.runtime import bootstrap_palm_server, shutdown_palm

    host = bootstrap_palm_server(host="127.0.0.1", port=8765)
    try:
        assert host.profile == HostProfile.server_only(host="127.0.0.1", port=8765)
        assert "server" in host.profile.roles
        runtime = host.app.runtime("server")
        assert runtime.base_url == "http://127.0.0.1:8765"
    finally:
        shutdown_palm()


def test_resolve_server_bind_invalid_port() -> None:
    with pytest.raises(CommandError, match="Invalid port"):
        resolve_server_bind(port=0)


@pytest.mark.django_db
def test_palm_doctor_mentions_server_mode() -> None:
    out = StringIO()
    call_command("palm", "doctor", stdout=out)
    output = out.getvalue()
    assert "server mode" in output
    assert "palm server" in output