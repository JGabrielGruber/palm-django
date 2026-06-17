from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_palm_doctor_succeeds() -> None:
    out = StringIO()
    call_command("palm", "doctor", stdout=out)
    output = out.getvalue()
    assert "All checks passed" in output
    assert "[Catalog]" in output
    assert "flow definitions: 1" in output