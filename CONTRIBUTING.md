# Contributing

Thank you for helping improve ConfigStream! The steps below set up the development environment.

## Setup

1. Install the runtime and development dependencies:
   ```bash
   pip install -e .[dev]
   ```
2. Install the pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Before committing

Run all checks locally:
```bash
pre-commit run --all-files
```
This executes `flake8`, `mypy` and `pytest` to ensure the codebase stays healthy.

Please also update `CHANGELOG.md` with a summary of your changes.

