from __future__ import annotations

from pathlib import Path

import pytest

import configstream.core.file_utils as file_utils_module


def test_find_project_root_success(fs, monkeypatch):
    """Test that find_project_root successfully finds the marker file."""
    # The `fs` fixture chdirs into a temporary directory.
    # We create the marker in the current directory.
    project_root = fs.create_file("pyproject.toml").parent
    src_dir = fs.create_dir("src")

    # Patch the __file__ attribute to simulate running from within the project
    monkeypatch.setattr(file_utils_module, "__file__", str(src_dir / "file.py"))

    # find_project_root should find the marker in the current working directory.
    assert file_utils_module.find_project_root() == project_root


def test_find_project_root_not_found(fs, monkeypatch):
    """Test that find_project_root raises FileNotFoundError when the marker is not found."""
    # No marker file is created.
    # We need to patch __file__ to a path that doesn't have the marker in its parents.
    # The fs fixture provides an isolated environment.
    monkeypatch.setattr(file_utils_module, "__file__", str(fs.root / "src" / "file.py"))

    with pytest.raises(FileNotFoundError, match="Project root marker 'pyproject.toml' not found."):
        file_utils_module.find_project_root()


def test_find_project_root_custom_marker(fs, monkeypatch):
    """Test that find_project_root works with a custom marker."""
    project_root = fs.create_file(".git").parent
    src_dir = fs.create_dir("src")

    monkeypatch.setattr(file_utils_module, "__file__", str(src_dir / "file.py"))

    assert file_utils_module.find_project_root(marker=".git") == project_root


def test_find_project_root_at_root(fs, monkeypatch):
    """Test that find_project_root can find the marker when CWD is the root."""
    # fs fixture sets CWD to fs.root. We create the marker here.
    fs.create_file("pyproject.toml")
    project_root = Path.cwd()  # which is fs.root

    # Create a src dir and simulate running from there.
    src_dir = fs.create_dir("src")
    monkeypatch.setattr(file_utils_module, "__file__", str(src_dir / "file.py"))

    # The function should find the marker in the CWD.
    assert file_utils_module.find_project_root() == project_root


def test_find_marker_from_none(fs):
    """Ensure find_marker_from returns None when marker is absent."""
    # Just create a directory and check from there. No marker exists.
    base_dir = fs.create_dir("some/deep/path")
    assert file_utils_module.find_marker_from(base_dir) is None