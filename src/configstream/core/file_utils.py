# ConfigStream
# Copyright (C) 2025 Amirreza "Farnam" Taheri
# This program comes with ABSOLUTELY NO WARRANTY; for details type `show w`.
# This is free software, and you are welcome to redistribute it
# under certain conditions; type `show c` for details.
# For more information, see <https://amirrezafarnamtaheri.github.io/configStream/>.

from __future__ import annotations

from pathlib import Path
from typing import Iterable


def _walk_upwards(start_dir: Path, marker: str) -> Path | None:
    """Return the first parent directory containing ``marker`` or ``None``."""

    current_dir = start_dir
    while True:
        if (current_dir / marker).exists():
            return current_dir
        if current_dir == current_dir.parent:
            return None
        current_dir = current_dir.parent


def find_marker_from(start_dir: Path, marker: str = "pyproject.toml") -> Path | None:
    """Public helper to locate ``marker`` starting from ``start_dir``."""

    return _walk_upwards(start_dir.resolve(), marker)


def find_project_root(marker: str = "pyproject.toml") -> Path:
    """Find the project root by searching from sensible starting locations.

    The original implementation searched relative to this module's location.
    That works when running from the installed package, but makes unit tests
    that rely on temporary working directories difficult without ``pyfakefs``.
    We now try multiple starting points, prioritising the current working
    directory so tests can operate in isolated sandboxes, and falling back to
    the module location for the default behaviour.
    """

    start_points: Iterable[Path] = (
        Path.cwd(),
        Path(__file__).resolve().parent,
    )
    for start in start_points:
        result = _walk_upwards(start, marker)
        if result is not None:
            return result
    raise FileNotFoundError(f"Project root marker '{marker}' not found.")
