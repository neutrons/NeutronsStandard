# PythonCommons

Common software utilities and architecture tools for neutrons Python projects. This repository provides only reusable infrastructure components.

## Purpose

This package centralizes cross-cutting architectural concerns that are useful across multiple neutrons projects:

- **Configuration Management** (`config.py`) - YAML-based configuration with environment layering and token substitution
- **Singleton Pattern** (`singleton.py`) - Decorator for enforcing single-instance patterns
- **Time Utilities** (`time.py`) - High-precision timestamp generation and parsing
- Other infrastructure utilities and design patterns

Domain-specific scientific utilities should be implemented in project-specific repositories, not here.

## Quick Start

### Install Pixi

```bash
curl -fsSL https://pixi.sh/install.sh | bash
```

### Set Up Environment

```bash
pixi install
```

### Run Tests

```bash
pixi run test
```

## Using This Package

Add `PythonCommons` as a dependency to your project:

```toml
# In your pyproject.toml
dependencies = [
    "PythonCommons @ git+https://github.com/neutrons/PythonCommons.git",
]
```

or

```toml
[tool.pixi.workspace]
channels = [
  "neutrons",
  "conda-forge",
  "https://prefix.dev/pixi-build-backends",
]

[tool.pixi.dependencies]
neutrons_standard = "*"

[tool.pixi.package.run-dependencies]
neutrons_standard = "*"
```

Then import utilities:

```python
from neutrons_standard import Config
from neutrons_standard.decorators.singleton import Singleton
from neutrons_standard.time import timestamp, isoFromTimestamp
```

See [`readthedocs`](https://pythoncommons.readthedocs.io/en/latest/) for detailed documentation on each module.

## Development

### Available Tasks

```bash
pixi run         # List all tasks
pixi run test    # Run tests
pixi run build-docs  # Build documentation
```

### Development Workflow

```bash
pixi shell                      # Activate environment
python -m pytest tests/         # Run tests
ruff check .                    # Lint code
```

## Testing

Run the test suite:

```bash
pixi run test
```

Tests are located in `tests/` and use pytest.

## Documentation

Documentation is built with Sphinx:

```bash
pixi run build-docs
```

Output will be in `docs/_build/html/`.

## Project Structure

```
PythonCommons/
├── src/neutrons_standard/              # Main package
│   ├── config.py             # Configuration management
│   ├── time.py               # Time utilities
│   └── decorators/
│       └── singleton.py       # Singleton pattern decorator
├── tests/                    # Test suite
├── docs/                     # Documentation (Sphinx)
├── pyproject.toml            # Project metadata and Pixi tasks
└── pixi.lock                 # Locked dependencies
```

## Known Issues

### SQLite file locking on shared mounts

On SNS Analysis systems, `pixi run conda-build` may fail due to sqlite3 file locking on shared mounts. This is a known limitation when user directories are network shares.

### Dynamic versioning and lock file circular dependency

When using pixi with editable self-dependencies and git-based versioning, there's a circular dependency issue. The solution uses pixi's `--skip` flag:

```bash
pixi install --frozen --skip PythonCommons
pip install --no-deps -e .
```
