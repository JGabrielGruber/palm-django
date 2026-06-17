"""Internal helpers for Django lifecycle edge cases."""

from __future__ import annotations

import sys


def is_migration_command() -> bool:
    return len(sys.argv) > 1 and sys.argv[1] in {
        "makemigrations",
        "migrate",
        "sqlmigrate",
        "showmigrations",
        "squashmigrations",
    }