# Changelog

All notable changes to palm-django are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

_No changes yet._

## [0.9.0] — 2026-06-25

**palmengine 0.13.x support** — requires [Palm Engine](https://palmengine.org) 0.13.13+ (Wizard Experience, ProviderApp framework, `/v1/wizards` REST).

Requires **Python 3.11+**, **Django 4.2+**, and **palmengine 0.13.13+**.

### Changed

- **Dependency** — `palmengine>=0.13.13` (drops 0.12.x compatibility)

## [0.8.0] — 2026-06-17

**First PyPI release** — production-ready Django integration for [Palm Engine](https://palmengine.org) 0.12.x.

Requires **Python 3.11+**, **Django 4.2+**, and **palmengine 0.12.9+**.

### Added

- **Django app bootstrap** — `palm_django` in `INSTALLED_APPS` starts a process-wide `ApplicationHost` on `AppConfig.ready()`
- **`PALM` / `PALM_*` settings bridge** — Django settings map to `PalmSettings`; Django ORM is the default `storage_backend`
- **Auto-discovery** — scans each installed app for `palm_definitions` or `palm` modules (`register_definitions`, `register_resources`, `register_commit_handlers`)
- **Django ORM storage** — `PalmDefinition`, `PalmProcessInstance`, `PalmStorageEntry` models with initial migration
- **`DjangoStorageBackend`** — Palm `BaseBackend` backed by Django models
- **Django model resources** — `@as_palm_resource` decorator and `PalmResourceModel` base; auto-registers CRUD at `{app_label}.{model}.{action}`
- **`DjangoModelProvider`** — Palm provider (`django_model`) with transactional ORM mutations
- **Auto-generated schemas** — `schema=True` builds `DictStateSchema` from Django fields; registers `StateSchemaDefinition` refs; validates create/update payloads
- **Transaction bridging** — `palm_atomic()` and `django_atomic()` join Django `transaction.atomic()` without redundant savepoints
- **Signals** — `palm_resource_invoked`, `palm_model_saved`
- **Django Admin** — browse definitions, instances, storage entries; admin actions to start flows and resume instances
- **Management commands** — unified `python manage.py palm`:
  - `doctor` (human + `--json`)
  - `quickstart` (scaffold snippets)
  - `server` / `host server` — `ServerRuntime` + Palm Explorer SSR hub
  - `run`, `flow`, `instance`, `resource` subcommands (list, start, resume, invoke)
- **Public API** — `get_host()`, `get_app()`, `get_runtime()`, `bootstrap_palm()`, `shutdown_palm()`, settings helpers

### Notes

- Wizard resource steps require `step_kind: resource`, `resource_ref`, and explicit `action` (e.g. `create`); omitting `action` defaults to `fetch`
- Palm Explorer `/explorer/schemas` lists **flow** state schemas only; Django model schemas appear under `/explorer/resources`
- Link flow steps to model schemas with `state_schema_ref: "myapp.order.data"`

[0.8.0]: https://github.com/JGabrielGruber/palm-django/releases/tag/v0.8.0