"""Shared pytest fixtures for palm-django."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _ensure_palm_bootstrapped(db: None) -> None:
    """Bootstrap Palm after migrations are applied (pytest-django runs migrate first)."""
    from palm_django import bootstrap_palm, is_palm_started

    if not is_palm_started():
        bootstrap_palm()