# =============================================================================
# palm-django — Justfile
# PyPI distribution: palm-django · Django app: palm_django
# Run `just --list` to see all commands
# =============================================================================

package := "palm-django"
dist_dir := "dist"

default:
    just --list --unsorted

# -----------------------------------------------------------------------------
# Quality
# -----------------------------------------------------------------------------
check:
    ruff check .
    pytest
    @echo "✅ Quality gates passed"

# -----------------------------------------------------------------------------
# Packaging & Release (PyPI name: palm-django)
# -----------------------------------------------------------------------------
clean-dist:
    rm -rf {{dist_dir}} build *.egg-info palm_django.egg-info
    @echo "🧼 Cleaned build artifacts"

build: clean-dist
    uv build
    @ls -lh {{dist_dir}}/
    @echo "✅ Built {{package}} wheel + sdist in {{dist_dir}}/"

install-local:
    uv pip install --reinstall -e ".[dev]"
    @echo "✅ Editable install: {{package}} (import: palm_django)"

publish-test: build
    @echo "📤 Publishing {{package}} to TestPyPI (test.pypi.org)..."
    @test -n "${TEST_PYPI_TOKEN:-}" || (echo "Set TEST_PYPI_TOKEN (PyPI API token for TestPyPI)" && exit 1)
    uv publish --publish-url https://test.pypi.org/legacy/ --token "${TEST_PYPI_TOKEN}"
    @echo "✅ Published to TestPyPI. Try: pip install -i https://test.pypi.org/simple/ palm-django"

publish: build
    @echo "⚠️  WARNING: Publishing {{package}} to PRODUCTION PyPI!"
    @echo "    Verify version in pyproject.toml and CHANGELOG.md first."
    @echo "    Press Ctrl+C within 5 seconds to abort..."
    @sleep 5
    @test -n "${PYPI_TOKEN:-}" || (echo "Set PYPI_TOKEN (PyPI API token)" && exit 1)
    uv publish --token "${PYPI_TOKEN}"
    @echo "✅ Published to PyPI. Users can: pip install palm-django"

release-prep:
    @echo "📋 Release prep for {{package}} — see RELEASE-0.8.0.md"
    @echo "   Version: $(uv run python -c 'import palm_django; print(palm_django.__version__)')"
    just check
    just build
    @echo "🎉 Release prep complete — review dist/, CHANGELOG.md, RELEASE-0.8.0.md"

help:
    @echo "🌴 palm-django commands:"
    @echo "   just check            → ruff + pytest"
    @echo "   just build            → Clean + wheel + sdist"
    @echo "   just install-local    → Editable install with dev extras"
    @echo "   just publish-test     → Build + TestPyPI"
    @echo "   just publish          → Build + PyPI (5s warning)"
    @echo "   just release-prep     → check + build + checklist reminder"
    @echo "Run 'just --list' for full list"