from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from massconfigmerger.source_operations import (
    add_source,
    handle_add_source,
    handle_list_sources,
    handle_remove_source,
    list_sources,
    remove_source,
)


@pytest.fixture
def sources_file(tmp_path: Path) -> Path:
    file = tmp_path / "sources.txt"
    content = "http://source1.com\nhttp://source2.com\n"
    file.write_text(content)
    return file


def test_list_sources(sources_file: Path):
    sources = list_sources(sources_file)
    assert sources == ["http://source1.com", "http://source2.com"]


def test_list_sources_file_not_found(tmp_path: Path):
    non_existent_file = tmp_path / "not_found.txt"
    sources = list_sources(non_existent_file)
    assert sources == []


def test_add_source(sources_file: Path):
    new_url = "http://source3.com"
    added = add_source(sources_file, new_url)
    assert added is True
    sources = list_sources(sources_file)
    assert sources == ["http://source1.com", "http://source2.com", "http://source3.com"]


def test_add_existing_source(sources_file: Path):
    existing_url = "http://source1.com"
    added = add_source(sources_file, existing_url)
    assert added is False
    sources = list_sources(sources_file)
    assert sources == ["http://source1.com", "http://source2.com"]


def test_remove_source(sources_file: Path):
    url_to_remove = "http://source1.com"
    removed = remove_source(sources_file, url_to_remove)
    assert removed is True
    sources = list_sources(sources_file)
    assert sources == ["http://source2.com"]


def test_remove_non_existing_source(sources_file: Path):
    url_to_remove = "http://nonexistent.com"
    removed = remove_source(sources_file, url_to_remove)
    assert removed is False
    sources = list_sources(sources_file)
    assert sources == ["http://source1.com", "http://source2.com"]


def test_handle_list_sources(sources_file: Path, capsys):
    args = argparse.Namespace(sources_file=str(sources_file))
    handle_list_sources(args)
    captured = capsys.readouterr()
    assert "http://source1.com" in captured.out
    assert "http://source2.com" in captured.out


def test_handle_list_sources_empty(tmp_path: Path, capsys):
    sources_file = tmp_path / "empty.txt"
    sources_file.touch()
    args = argparse.Namespace(sources_file=str(sources_file))
    handle_list_sources(args)
    captured = capsys.readouterr()
    assert "No sources found" in captured.out


@patch("massconfigmerger.source_operations._is_public_url", return_value=True)
def test_handle_add_source_success(mock_is_public, sources_file: Path, capsys):
    new_url = "http://source3.com"
    args = argparse.Namespace(sources_file=str(sources_file), url=new_url)
    handle_add_source(args)
    captured = capsys.readouterr()
    assert f"Source added: {new_url}" in captured.out


def test_handle_remove_source_success(sources_file: Path, capsys):
    url_to_remove = "http://source1.com"
    args = argparse.Namespace(sources_file=str(sources_file), url=url_to_remove)
    handle_remove_source(args)
    captured = capsys.readouterr()
    assert f"Source removed: {url_to_remove}" in captured.out