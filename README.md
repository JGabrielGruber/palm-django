# palm-django

First-class [Django](https://www.djangoproject.com/) integration for [Palm Engine](https://palmengine.org) — the Python-first Behavior Tree orchestrator.

Turn Palm into a natural part of any Django project: bootstrap on app `ready()`, `PALM_*` settings bridge, auto-discovery of definitions from your apps, and `manage.py palm doctor` for health checks.

## Requirements

- Python 3.11+
- Django 4.2+
- [palmengine](https://pypi.org/project/palmengine/) 0.12.9+

## Installation

```bash
pip install palm-django
```

Or from source:

```bash
pip install -e ".[dev]"
```

## Quick start

### 1. Add to `INSTALLED_APPS`

```python
# settings.py

INSTALLED_APPS = [
    # ...
    "palm_django",
]
```

On startup, `palm_django` bootstraps a process-wide `ApplicationHost` and scans your Django apps for Palm hooks.

### 2. Run migrations

Django ORM is the default storage backend. Apply palm-django tables before first use:

```bash
python manage.py migrate palm_django
```

### 3. Configure Palm (optional)

Use a `PALM` dict and/or individual `PALM_*` settings. Keys accept either `STORAGE_BACKEND` (Django style) or `storage_backend` (Palm style).

```python
# settings.py

PALM = {
    # Default is django ORM — override only when needed:
    # "STORAGE_BACKEND": "memory",
    "LOAD_EXAMPLE_DEFINITIONS": False,
    "HOST_PROFILE": "all_in_one",
}

# palm-django integration options (not forwarded to PalmSettings)
PALM_AUTO_START = True
PALM_DISCOVERY_MODULES = ("palm_definitions", "palm")
```

Defaults are tuned for Django projects (no bundled Palm examples, lightweight startup).

### 4. Register definitions in your apps

Create `myapp/palm_definitions.py`:

```python
from palm.common.persistence.definition_repository import DefinitionRepository
from palm.definitions.flow import FlowDefinition


def register_definitions(repository: DefinitionRepository) -> None:
    repository.register_flow(
        FlowDefinition(
            id="hello_flow",
            name="hello_flow",
            pattern="sequence",
            options={},
        )
    )
```

`palm_django` imports `register_definitions` from each installed app automatically.

Supported hooks (all optional, per app):

| Module suffix        | Hook                      |
|----------------------|---------------------------|
| `palm_definitions`   | `register_definitions()`  |
| `palm_definitions`   | `register_resources()`    |
| `palm_definitions`   | `register_commit_handlers()` |
| `palm`               | same hooks (alternate name) |

### 5. Use Palm in your code

```python
from palm_django import get_host

def start_onboarding(user_id: str):
    return get_host().submit_flow("onboard", metadata={"user_id": user_id})
```

Or access the infrastructure layer directly:

```python
from palm_django import get_app

flows = get_app().list_flows()
```

### 6. Run the doctor

```bash
python manage.py palm doctor
```

Reports versions, runtime health, storage status, discovery results, and catalog counts.

## Public API

| Symbol | Description |
|--------|-------------|
| `get_host()` | Process-wide `ApplicationHost` |
| `get_app()` | `PalmApp` infrastructure layer |
| `get_runtime()` | `PalmRuntime` wrapper with discovery metadata |
| `bootstrap_palm()` | Idempotent manual bootstrap |
| `shutdown_palm()` | Graceful shutdown |
| `is_palm_started()` | Whether the host is running |
| `get_palm_settings()` | `PalmSettings` built from Django settings |
| `build_palm_settings_dict()` | Raw merged settings dict |
| `DjangoStorageBackend` | Palm `BaseBackend` backed by Django ORM |
| `palm_atomic()` | Context manager for transactional Palm + Django writes |
| `storage_health_report()` | ORM table readiness and row counts |

## Storage

When `palm_django` is installed, **`django` is the default `storage_backend`**. Palm's key-value contract is preserved:

| Palm key pattern | Django model |
|------------------|--------------|
| `palm:definitions:{kind}:{id}` | `PalmDefinition` |
| `palm:instances:{instance_id}` | `PalmProcessInstance` (snapshots + status history in `data`) |
| Indexes, projections, outbox, other keys | `PalmStorageEntry` |

Override with `PALM_STORAGE_BACKEND = "memory"` or `"filesystem"` when needed.

Wrap multi-step Django + Palm work in a single transaction:

```python
from palm_django import get_host, palm_atomic

with palm_atomic():
    order = Order.objects.create(...)
    get_host().submit_flow("fulfill_order", metadata={"order_id": order.pk})
```

## Settings reference

### Palm settings (`PALM` dict / `PALM_*` attrs)

All fields from [`PalmSettings`](https://github.com/JGabrielGruber/palmengine) are supported. Common ones:

| Key | Default (Django) | Notes |
|-----|------------------|-------|
| `storage_backend` | `django` | Django ORM via `palm_django` models |
| `load_example_definitions` | `False` | Avoid Palm demo definitions in production |
| `host_profile` | `all_in_one` | Collapsed embedded runtime |
| `default_scheduler` | `inline` | Synchronous in-process execution |

### palm-django integration settings

| Setting | Default | Description |
|---------|---------|-------------|
| `PALM_AUTO_START` | `True` | Start `ApplicationHost` in `AppConfig.ready()` |
| `PALM_DISCOVERY_MODULES` | `("palm_definitions", "palm")` | Module suffixes to scan per app |
| `PALM_DISCOVER_DEFINITIONS` | `True` | Call `register_definitions` hooks |
| `PALM_DISCOVER_RESOURCES` | `True` | Call `register_resources` hooks |
| `PALM_DISCOVER_COMMIT_HANDLERS` | `True` | Call `register_commit_handlers` hooks |

## Development

```bash
git clone https://github.com/JGabrielGruber/palm-django.git
cd palm-django
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Roadmap

- `DjangoModelProvider` — any model as a Palm Resource
- Django Admin integration for Palm models
- `python manage.py palm run` and additional commands

## License

MIT