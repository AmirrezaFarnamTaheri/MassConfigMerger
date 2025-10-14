from __future__ import annotations

from pathlib import Path

import pytest

import configstream.core.file_utils as file_utils_module


def test_find_project_root_success(fs, monkeypatch):
    """Test that find_project_root successfully finds the marker file."""
    # Create a fake directory structure
    project_root = Path("/home/user/project")
    src_dir = project_root / "src"
    fs.create_dir(src_dir)
    fs.create_file(project_root / "pyproject.toml")

    # Patch the __file__ attribute to control the starting point of the search
    monkeypatch.setattr(file_utils_module, "__file__", str(src_dir / "file.py"))

    # Call the function and assert the result
    assert file_utils_module.find_project_root() == project_root


def test_find_project_root_not_found(fs, monkeypatch):
    """Test that find_project_root raises FileNotFoundError when the marker is not found."""
    # Create a directory structure without the marker file
    src_dir = Path("/home/user/project/src")
    fs.create_dir(src_dir)

    monkeypatch.setattr(file_utils_module, "__file__", str(src_dir / "file.py"))

    with pytest.raises(
        FileNotFoundError, match="Project root marker 'pyproject.toml' not found."
    ):
        file_utils_module.find_project_root()


def test_find_project_root_custom_marker(fs, monkeypatch):
    """Test that find_project_root works with a custom marker."""
    project_root = Path("/home/user/project")
    src_dir = project_root / "src"
    fs.create_dir(src_dir)
    fs.create_file(project_root / ".git")  # Custom marker

    monkeypatch.setattr(file_utils_module, "__file__", str(src_dir / "file.py"))

    assert file_utils_module.find_project_root(marker=".git") == project_root


def test_find_project_root_at_root(fs, monkeypatch):
    """Test that find_project_root can find the marker at the filesystem root."""
    src_dir = Path("/src")
    fs.create_dir(src_dir)
    fs.create_file("/pyproject.toml")

    monkeypatch.setattr(file_utils_module, "__file__", str(src_dir / "file.py"))

    assert file_utils_module.find_project_root() == Path("/")


def test_find_marker_from_none(fs):
    """Ensure find_marker_from returns None when marker is absent."""

    base_dir = Path("/home/user/project/src")
    fs.create_dir(base_dir)
    assert file_utils_module.find_marker_from(base_dir) is None
