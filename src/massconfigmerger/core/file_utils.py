from __future__ import annotations

from pathlib import Path

def find_project_root(marker: str = "pyproject.toml") -> Path:
    """
    Find the project root by searching upwards for a marker file.
    """
    current_dir = Path(__file__).resolve()
    while current_dir != current_dir.parent:
        if (current_dir / marker).exists():
            return current_dir
        current_dir = current_dir.parent
    raise FileNotFoundError(f"Project root marker '{marker}' not found.")