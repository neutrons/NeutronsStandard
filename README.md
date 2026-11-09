# Neutrons Standard

[![documentation](https://img.shields.io/badge/-Documentation-purple?logo=read-the-docs&logoColor=white&style=for-the-badge)](https://pythoncommons.readthedocs.io/en/latest/)

A set of common software utilities and architecture tools for neutrons Python projects.
This repository provides only reusable infrastructure components.

## Purpose

This package centralizes cross-cutting architectural concerns that are useful across multiple neutrons projects:

- **Configuration Management** (`config.py`) - YAML-based configuration with environment layering and token substitution
- **Singleton Pattern** (`singleton.py`) - Decorator for enforcing consistent single-instance object patterns
- **Time Utilities** (`time.py`) - High-precision timestamp generation and parsing
- Other infrastructure utilities and design patterns

Domain-specific scientific utilities should be implemented in project-specific repositories, not here.

## Table of Contents

- [Quick Start](#quick-start)
- [Development](#development)
- [Testing](#testing)

## Quick Start

1. Add `neutrons_standard` as a dependency to your project:

   **Using `pip`**:

   ```bash
   pip install git+https://github.com/neutrons/NeutronsStandard.git
   ```

   or add it to your `pyproject.toml`:

   ```toml
   dependencies = [
       "neutrons_standard @ git+https://github.com/neutrons/NeutronsStandard.git",
   ]
   ```

   **Using `pixi`**:

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

1. Initialize the package in your client code:

   ```python
   # in your client package's main entry point or __init__.py
   import neutrons_standard

   neutrons_standard.init("your_client_package_name")
   ```

   **NOTES**:
   - The `init()` function must be called before any other `neutrons_standard` functionality is used, and only once per process.
   - The `client_package_name` argument must be the importable name of your client package,
     which is used for configuration file paths and environment variable names.

1. Then import utilities:

   ```python
   from neutrons_standard import Config
   from neutrons_standard.decorators.singleton import Singleton
   from neutrons_standard.time import timestamp, iso_from_timestamp
   ```

See [`readthedocs`](https://pythoncommons.readthedocs.io/en/latest/) for detailed usage and documentation.

## Development

This package uses [pixi](https://pixi.prefix.dev/latest/#installation) for dependency management and development tasks.

### Setup

First, install pixi if needed, then clone the repository and install the package and its dependencies:

```bash
git clone https://github.com/neutrons/NeutronsStandard.git
cd NeutronsStandard
pixi install
```

### Available Tasks

```bash
pixi task list       # List all tasks

# some common tasks:
pixi run test        # Run tests
pixi run build-docs  # Build documentation
```

### Development Workflow

```bash
pixi shell               # Activate environment
python -m pytest tests/  # Run tests
ruff check .             # Lint code
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
NeutronsStandard/
├── src/neutrons_standard/    # Main package
│   ├── config.py             # Configuration management
│   ├── time.py               # Time utilities
│   └── decorators/
│       └── singleton.py      # Singleton pattern decorator
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
pixi install --frozen --skip NeutronsStandard
```
