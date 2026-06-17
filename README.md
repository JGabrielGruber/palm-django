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

### 5. Expose Django models as Palm resources

Decorate any model (or set a class-level ``palm_resource`` dict) and palm-django
auto-registers CRUD resources at bootstrap:

```python
from django.db import models
from palm_django import as_palm_resource

@as_palm_resource(actions=["get", "create", "update", "delete", "list"])
class Order(models.Model):
    customer_id = models.IntegerField()
    total = models.DecimalField(max_digits=12, decimal_places=2)
```

Resource names follow ``{app_label}.{model_name}.{action}`` — e.g.
``myapp.order.create``. Params bind from Palm state via ``{{ state.pk }}``,
``{{ state.data }}``, etc.; results promote to ``output_key`` (defaults to the
model name) in wizard/BT leaves.

```python
from palm_django import get_app

app = get_app()
result = app.invoke_resource(
    "myapp.order.create",
    state={"data": {"customer_id": 1, "total": "49.99"}},
)
```

Manual control remains available via ``register_resources()`` in
``palm_definitions.py`` for custom ``ResourceDefinition`` objects.

### 6. Use Palm in your code

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

### 7. Operator commands

```bash
# Health check
python manage.py palm doctor

# Start a flow or process (auto-detects kind)
python manage.py palm run sample_flow
python manage.py palm flow start onboard --metadata '{"user_id": 42}'

# Inspect catalog
python manage.py palm flow list
python manage.py palm instance list
python manage.py palm instance list --all
python manage.py palm resource list

# Invoke a resource with state binding
python manage.py palm resource invoke myapp.order.create \
  --state '{"data": {"customer_id": 1, "total": "10.00"}}'

# Resume a persisted instance
python manage.py palm instance resume <instance_id>
```

Commands bootstrap Palm automatically and run against the active Django database.

### 8. Django Admin

Add `django.contrib.admin` to `INSTALLED_APPS` to inspect Palm persistence models:

- **Palm definitions** — browse flows/processes/resources; admin action **Start flow**
- **Palm process instances** — browse instances; admin action **Resume**
- **Palm storage entries** — raw KV rows (projections, indexes, outbox)

```bash
python manage.py palm doctor   # confirms admin registration status
```

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
| `as_palm_resource` | Decorator to expose a Django model as Palm resources |
| `DjangoModelProvider` | Palm provider (`django_model`) backing ORM CRUD |
| `PalmResourceModel` | Optional base class for class-level ``palm_resource`` config |

## Django model resources

| Action | Params | State binding examples |
|--------|--------|------------------------|
| `get` | `model`, `pk` (or custom `lookup_field`) | `state.pk` |
| `list` | `model`, `filters`, `order_by`, `limit` | `state.filters` |
| `create` | `model`, `data` | `state.data` |
| `update` | `model`, `pk`, `data` | `state.pk`, `state.data` |
| `delete` | `model`, `pk` | `state.pk` |

Provider registry key: **`django_model`**. Mutating actions run inside
``transaction.atomic()``.

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

- Django Admin integration for Palm models
- `python manage.py palm run` and additional commands

## License

MIT