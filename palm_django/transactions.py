"""
Transaction bridging between Django ORM and Palm storage operations.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from django.db import transaction


@contextmanager
def palm_atomic(using: str | None = None) -> Iterator[None]:
    """
    Group Palm operations inside a Django database transaction.

    Palm's Django storage backend already wraps each ``get``/``set``/``delete``
    in ``atomic()``; nesting joins the surrounding transaction naturally.
    """
    with transaction.atomic(using=using):
        yield