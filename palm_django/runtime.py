"""
Process-wide Palm runtime singleton for Django.

Hosts a single :class:`~palm.app.host.ApplicationHost` per Django process,
started during :meth:`~palm_django.apps.PalmDjangoConfig.ready`.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from palm.app.host.application_host import ApplicationHost
from palm.app.settings import PalmSettings

from palm_django.discovery import DiscoveryReport, discover_and_register
from palm_django.settings import get_django_integration_settings, get_palm_settings

if TYPE_CHECKING:
    from palm.app.app import PalmApp


class PalmRuntime:
    """Django-scoped wrapper around ApplicationHost with discovery metadata."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._host: ApplicationHost | None = None
        self._discovery: DiscoveryReport | None = None
        self._started = False

    @property
    def host(self) -> ApplicationHost:
        if self._host is None:
            raise RuntimeError(
                "Palm runtime is not initialized. "
                "Ensure 'palm_django' is in INSTALLED_APPS and AppConfig.ready() has run."
            )
        return self._host

    @property
    def app(self) -> PalmApp:
        return self.host.app

    @property
    def is_started(self) -> bool:
        return self._started and self._host is not None and self._host.is_started

    @property
    def discovery(self) -> DiscoveryReport | None:
        return self._discovery

    def bootstrap(
        self,
        *,
        settings: PalmSettings | None = None,
        auto_start: bool | None = None,
        **start_options: Any,
    ) -> ApplicationHost:
        """Create (and optionally start) the process-wide ApplicationHost."""
        with self._lock:
            if self._host is not None and self._started:
                return self._host

            if self._host is not None and not self._started:
                if self._host.is_started:
                    self._host.shutdown()
                self._host = None

            palm_settings = settings or get_palm_settings()
            integration = get_django_integration_settings()
            should_start = integration["auto_start"] if auto_start is None else auto_start

            if self._host is None:
                self._host = ApplicationHost(settings=palm_settings)

            if should_start and not self._started:
                self._host.start(**start_options)
                self._started = True
                self._discovery = discover_and_register(
                    self._host.app.repository(),
                    discovery_modules=integration["discovery_modules"],
                    discover_definitions=integration["discover_definitions"],
                    discover_resources=integration["discover_resources"],
                    discover_commit_handlers=integration["discover_commit_handlers"],
                )
            return self._host

    def shutdown(self) -> None:
        with self._lock:
            if self._host is not None and self._host.is_started:
                self._host.shutdown()
            self._started = False
            self._host = None
            self._discovery = None


_runtime = PalmRuntime()


def get_runtime() -> PalmRuntime:
    return _runtime


def bootstrap_palm(**options: Any) -> ApplicationHost:
    """Bootstrap the process-wide Palm host (idempotent)."""
    return _runtime.bootstrap(**options)


def get_host() -> ApplicationHost:
    """Return the process-wide ApplicationHost, bootstrapping lazily if needed."""
    if not _runtime.is_started:
        bootstrap_palm()
    return _runtime.host


def get_app() -> PalmApp:
    """Return the PalmApp infrastructure layer, bootstrapping lazily if needed."""
    return get_host().app


def shutdown_palm() -> None:
    """Shut down the process-wide Palm host."""
    _runtime.shutdown()


def is_palm_started() -> bool:
    return _runtime.is_started