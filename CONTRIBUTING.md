# Contributing

Use Python 3.10+ and Node.js 22+. From a clean checkout:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m pip install -r requirements-dev.lock
npm ci
```

On Windows, use `.venv\Scripts\python.exe`. Set `OPENAPPLE_PYTHON` to that absolute executable when running the desktop. `openapple setup` provides an isolated user runtime for an installed npm distribution.

Run checks before submitting:

```sh
python -m ruff check openapple tests
python -m ruff format --check openapple tests
python -m mypy openapple
python -m pytest -q
npm run format:check
npm run check
npm test
python -m build --no-isolation
npm pack
python scripts/check_artifacts.py
```

Activate your virtual environment first. Tests use temporary data/config directories and do not launch a GUI or type into other applications. Node integration tests bind ephemeral loopback ports. A restricted sandbox must permit that local networking. Do not disable the tests to work around a sandbox failure.

Add behavioral regression tests for approval, persistence, protocol, or setup changes. Never use your real orchard/config files as fixtures. Keep model celebration labels clearly fictional. See [architecture](docs/ARCHITECTURE.md) and [manual validation](docs/VALIDATION.md) for boundaries and platform checks.

On Linux, `npm run test:desktop` additionally exercises real Electron preload and review controls headlessly in a temporary orchard. It opens ephemeral local debugging ports and closes the test instance afterward. Use the native checklist for macOS/Windows.

For a full distribution bootstrap test, run `python scripts/check_installation.py` after packing. It downloads runtime dependencies and writes only temporary test data and configuration.
