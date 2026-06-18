# Release checklist — 0.8.0

First PyPI release: Django integration for Palm Engine — ORM storage, model resources, schemas, `manage.py palm`, and Palm Explorer server.

## Pre-release verification

- [ ] Version bumped: `pyproject.toml` and `palm_django/__init__.py` → **0.8.0**
- [ ] `CHANGELOG.md` — `[0.8.0]` section complete; `[Unreleased]` empty
- [ ] `README.md` — install, quickstart, features, publishing notes current
- [ ] `LICENSE` present (MIT)

## Quality gates

```bash
just check            # ruff + pytest
just build            # wheel + sdist in dist/
ls -lh dist/          # palm_django-0.8.0-*
```

Expected: **60 tests** pass.

Manual smoke (sample project or your Django app):

```bash
python manage.py migrate palm_django
python manage.py palm doctor
python manage.py palm doctor --json
python manage.py palm resource list
python manage.py palm flow list
python manage.py palm server          # http://127.0.0.1:8080/explorer
```

## Build & publish

### Local (optional)

```bash
just build
export TEST_PYPI_TOKEN=pypi-...   # TestPyPI API token
just publish-test
pip install -i https://test.pypi.org/simple/ 'palm-django==0.8.0'
python -c "import palm_django; print(palm_django.__version__)"
```

```bash
export PYPI_TOKEN=pypi-...
just publish                   # 5s abort window
```

### CI (recommended — same as palmengine)

Set repository secrets:

| Secret | Purpose |
|--------|---------|
| `PYPI_TOKEN` | Production PyPI API token |
| `TEST_PYPI_TOKEN` | TestPyPI API token (optional, for manual workflow runs) |

## Git tag & GitHub release

```bash
git add -A
git commit -m "Release 0.8.0 — Django integration for Palm Engine"
git tag -a v0.8.0 -m "palm-django 0.8.0 — Django integration for Palm Engine"
git push origin master --tags
```

Create a **GitHub release** from tag `v0.8.0`:

- Title: **palm-django 0.8.0 — Django integration for Palm Engine**
- Body: copy the `[0.8.0]` section from `CHANGELOG.md`
- Click **Publish release** — `.github/workflows/publish.yml` builds and uploads to PyPI automatically

To test CI without a release, use **Actions → Publish to PyPI → Run workflow** with target `testpypi`.

## Post-release

- [ ] Verify `pip install palm-django` on a clean venv
- [ ] Confirm [PyPI project page](https://pypi.org/project/palm-django/) shows 0.8.0
- [ ] Open `[Unreleased]` in `CHANGELOG.md` for next work

## Notes for release body

- Requires **palmengine 0.12.9+** and **Django 4.2+**
- Wizard resource steps need explicit `action` (e.g. `create`); omitting it defaults to `fetch`
- Model schemas appear under `/explorer/resources`, not `/explorer/schemas` (flow schemas only)