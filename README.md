# palm-django

First-class [Django](https://www.djangoproject.com/) integration for [Palm Engine](https://palmengine.org) — the Python-first Behavior Tree orchestrator.

Turn Palm into a natural part of any Django project: bootstrap on app `ready()`, `PALM_*` settings bridge, auto-discovery of definitions from your apps, Django ORM storage, model resources, signals, transactional bridging, and `manage.py palm` operator commands.

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

### 4. Scaffold with quickstart (optional)

```bash
python manage.py palm quickstart
python manage.py palm quickstart --app myapp
python manage.py palm quickstart --app myapp --write   # writes myapp/palm_definitions.py
```

### 5. Register definitions in your apps

Create `myapp/palm_definitions.py`:

```python
from palm.common.persistence.definition_repository import DefinitionRepository
from palm.definitions.flow import FlowDefinition


def register_definitions(repository: DefinitionRepository) -> None:
    repository.register_flow(
        FlowDefinition(
            id="hello_flow",
            name="hello_flow",
            pattern="dag",
            options={"name": "hello_flow"},
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

### 6. Expose Django models as Palm resources

Decorate any model (or set a class-level ``palm_resource`` dict) and palm-django auto-registers CRUD resources at bootstrap:

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

### 7. Wizard + Django model resources

Use Palm 0.12 ``step_kind: resource`` with ``resource_ref`` pointing at your auto-registered model resources:

```python
FlowDefinition(
    id="flow-onboard-order",
    name="onboard_order",
    pattern="wizard",
    options={
        "include_summary": True,
        "steps": [
            {
                "slug": "customer_id",
                "title": "Customer",
                "prompt": "Enter customer id",
                "validation": [{"rule": "not_empty"}],
            },
            {
                "slug": "create-order",
                "title": "Create order",
                "step_kind": "resource",
                "resource_ref": "myapp.order.create",
                "action": "create",
                "params": {
                    "data": {
                        "customer_id": "{{ state.customer_id }}",
                        "total": "{{ state.total }}",
                    }
                },
                "output_key": "order",
            },
        ],
    },
)
```

See `tests/palm_sample/palm_definitions.py` for a full working example (`item_wizard`).

### 8. Use Palm in your code

```python
from palm_django import get_host, palm_atomic

def start_onboarding(user_id: str):
    return get_host().submit_flow("onboard", metadata={"user_id": user_id})

# Roll back Palm storage + ORM writes together
with palm_atomic():
    order = Order.objects.create(customer_id=1, total="10.00")
    get_host().submit_flow("fulfill_order", metadata={"order_id": order.pk})
```

Or access the infrastructure layer directly:

```python
from palm_django import get_app

flows = get_app().list_flows()
```

### 9. Operator commands

```bash
# Health check (human-readable or JSON)
python manage.py palm doctor
python manage.py palm doctor --json

# Palm Explorer (ServerRuntime + SSR hub) — foreground until Ctrl+C
python manage.py palm server
python manage.py palm host server          # alias
python manage.py palm server --port 9000
python manage.py palm server --host 0.0.0.0 --port 8080

# Scaffold snippets
python manage.py palm quickstart --app myapp

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

#### Palm Explorer server

`palm server` starts a full `ServerRuntime` with the Palm Explorer SSR surface. It uses your Django database (ORM storage), discovered flows/resources, and `PALM_*` settings:

```bash
python manage.py palm server
# Palm Explorer available at http://127.0.0.1:8080/explorer
```

Configure bind address via `PALM_SERVER_HOST` / `PALM_SERVER_PORT` or CLI `--host` / `--port`. Press Ctrl+C for graceful shutdown.

### 10. Django Admin

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
| `django_atomic()` | Join outer `atomic()` without redundant savepoints |
| `storage_health_report()` | ORM table readiness and row counts |
| `as_palm_resource` | Decorator to expose a Django model as Palm resources |
| `DjangoModelProvider` | Palm provider (`django_model`) backing ORM CRUD |
| `palm_resource_invoked` | Signal after successful provider invocation |
| `palm_model_saved` | Signal when a decorated model is saved via ORM |
| `PalmResourceModel` | Optional base class for class-level ``palm_resource`` config |

## Django model resources

| Action | Params | State binding examples |
|--------|--------|------------------------|
| `get` | `model`, `pk` (or custom `lookup_field`) | `state.pk` |
| `list` | `model`, `filters`, `order_by`, `limit` | `state.filters` |
| `create` | `model`, `data` | `state.data` |
| `update` | `model`, `pk`, `data` | `state.pk`, `state.data` |
| `delete` | `model`, `pk` | `state.pk` |

Provider registry key: **`django_model`**. Mutating actions join the current Django transaction when one is active.

## Signals

Connect to Palm lifecycle events in your Django apps:

```python
from django.dispatch import receiver
from palm_django import palm_model_saved, palm_resource_invoked


@receiver(palm_resource_invoked)
def on_resource_invoked(sender, provider, action, model_label, params, result, **kwargs):
    audit_log.info("palm %s %s on %s", provider, action, model_label)


@receiver(palm_model_saved)
def on_model_saved(sender, instance, created, model_label, **kwargs):
    if created:
        notify_team(instance)
```

`palm_model_saved` fires for direct ORM saves on decorated models. Saves performed inside Palm provider mutations emit `palm_resource_invoked` instead (no duplicate model signal).

## Storage

When `palm_django` is installed, **`django` is the default `storage_backend`**. Palm's key-value contract is preserved:

| Palm key pattern | Django model |
|------------------|--------------|
| `palm:definitions:{kind}:{id}` | `PalmDefinition` |
| `palm:instances:{instance_id}` | `PalmProcessInstance` (snapshots + status history in `data`) |
| Indexes, projections, outbox, other keys | `PalmStorageEntry` |

Override with `PALM_STORAGE_BACKEND = "memory"` or `"filesystem"` when needed.

### Transaction bridging

`palm_atomic()` and internal `django_atomic()` join an existing `transaction.atomic()` block instead of opening redundant savepoints. Palm storage writes and model provider mutations roll back with surrounding Django work:

```python
from django.db import transaction
from palm_django import get_app, palm_atomic

with transaction.atomic():
    app.invoke_resource("myapp.order.create", state={...})
    # raises → ORM row and Palm KV writes roll back together
```

## Settings reference

### Palm settings (`PALM` dict / `PALM_*` attrs)

All fields from [`PalmSettings`](https://github.com/JGabrielGruber/palmengine) are supported. Common ones:

| Key | Default (Django) | Notes |
|-----|------------------|-------|
| `storage_backend` | `django` | Django ORM via `palm_django` models |
| `load_example_definitions` | `False` | Avoid Palm demo definitions in production |
| `host_profile` | `all_in_one` | Collapsed embedded runtime |
| `server_host` | `127.0.0.1` | Bind host for `palm server` |
| `server_port` | `8080` | Bind port for `palm server` |
| `default_scheduler` | `inline` | Synchronous in-process execution |

### palm-django integration settings

| Setting | Default | Description |
|---------|---------|-------------|
| `PALM_AUTO_START` | `True` | Start `ApplicationHost` in `AppConfig.ready()` |
| `PALM_DISCOVERY_MODULES` | `("palm_definitions", "palm")` | Module suffixes to scan per app |
| `PALM_DISCOVER_DEFINITIONS` | `True` | Call `register_definitions` hooks |
| `PALM_DISCOVER_RESOURCES` | `True` | Call `register_resources` hooks |
| `PALM_DISCOVER_COMMIT_HANDLERS` | `True` | Call `register_commit_handlers` hooks |

## Common patterns

| Goal | Approach |
|------|----------|
| CRUD from flows/wizards | `@as_palm_resource` + `step_kind: resource` |
| Custom resource logic | `register_resources()` with `ResourceDefinition` |
| Atomic business transaction | `with palm_atomic():` around ORM + Palm calls |
| React to Palm writes | `@receiver(palm_resource_invoked)` |
| React to direct ORM saves | `@receiver(palm_model_saved)` |
| Ops / debugging | `python manage.py palm doctor` |
| Browser Explorer | `python manage.py palm server` |
| New project bootstrap | `python manage.py palm quickstart --app myapp` |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `storage tables are missing` | `python manage.py migrate palm_django` |
| `ApplicationHost is not started` | Run migrations; check `PALM_AUTO_START`; run `palm doctor` |
| Resource not found | Use `palm resource list`; names are `{app_label}.{model}.{action}` |
| `Unknown Django model` | Use `app_label.ModelName` (e.g. `myapp.Order`), not dotted module path |
| Wizard resource step fails | Use `step_kind: resource` + `resource_ref`; set step `action` (e.g. `create`) — defaults to `fetch` if omitted |
| Flow not listed | Add `myapp/palm_definitions.py` with `register_definitions()` |
| Admin models missing | Add `django.contrib.admin` to `INSTALLED_APPS` |
| DB access during app init warning | Harmless during bootstrap before migrations; disappears after migrate |

```bash
python manage.py palm doctor        # full report + next-step tips
python manage.py palm doctor --json # machine-readable output
```

## Development

```bash
git clone https://github.com/JGabrielGruber/palm-django.git
cd palm-django
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
```

The `tests/palm_sample/` app demonstrates discovery, model resources, wizard flows, commands, admin, signals, and transaction bridging.

## License

MIT