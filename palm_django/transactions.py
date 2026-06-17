"""
Transaction bridging between Django ORM and Palm storage operations.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from django.db import transaction

_palm_mutation_depth: ContextVar[int] = ContextVar("_palm_mutation_depth", default=0)


def in_palm_mutation() -> bool:
    """Return whether the current context is executing a Palm-backed model mutation."""
    return _palm_mutation_depth.get() > 0


@contextmanager
def palm_mutation() -> Iterator[None]:
    """Mark the current context as a Palm provider mutation (suppresses duplicate signals)."""
    token = _palm_mutation_depth.set(_palm_mutation_depth.get() + 1)
    try:
        yield
    finally:
        _palm_mutation_depth.reset(token)


@contextmanager
def palm_atomic(using: str | None = None) -> Iterator[None]:
    """
    Group Palm operations inside a Django database transaction.

    Nested calls join the active transaction via Django savepoints, so Palm
    storage and ORM writes roll back together when an error escapes the block.
    """
    with django_atomic(using=using):
        yield


@contextmanager
def django_atomic(using: str | None = None) -> Iterator[None]:
    """
    Enter ``transaction.atomic()``.

    When already inside an outer ``atomic()`` block, Django opens a savepoint so
    Palm storage and provider mutations can roll back independently while still
    participating in the surrounding transaction.
    """
    with transaction.atomic(using=using):
        yield