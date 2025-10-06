from __future__ import annotations

import argparse
import socket
from pathlib import Path
from unittest.mock import patch

import pytest

from massconfigmerger.source_operations import (
    _is_public_url,
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


def test_add_source_creates_file(tmp_path: Path):
    """Test that add_source creates the file if it doesn't exist."""
    sources_file = tmp_path / "new_sources.txt"
    new_url = "http://source.com"
    added = add_source(sources_file, new_url)
    assert added is True
    assert sources_file.exists()
    assert sources_file.read_text() == f"{new_url}\n"


@patch("massconfigmerger.source_operations._is_public_url", return_value=False)
def test_handle_add_source_non_public(mock_is_public, sources_file: Path, capsys):
    """Test handle_add_source with a non-public URL."""
    url = "http://localhost/source"
    args = argparse.Namespace(sources_file=str(sources_file), url=url)
    handle_add_source(args)
    captured = capsys.readouterr()
    assert f"URL does not point to a public IP address: {url}" in captured.out


@patch("massconfigmerger.source_operations._is_public_url", return_value=True)
def test_handle_add_source_existing(mock_is_public, sources_file: Path, capsys):
    """Test handle_add_source when the source already exists."""
    url = "http://source1.com"
    args = argparse.Namespace(sources_file=str(sources_file), url=url)
    handle_add_source(args)
    captured = capsys.readouterr()
    assert f"Source already exists: {url}" in captured.out


def test_handle_remove_source_not_found(sources_file: Path, capsys):
    """Test handle_remove_source when the source is not found."""
    url = "http://nonexistent.com"
    args = argparse.Namespace(sources_file=str(sources_file), url=url)
    handle_remove_source(args)
    captured = capsys.readouterr()
    assert f"Source not found: {url}" in captured.out


@patch("socket.gethostbyname")
def test_is_public_url(mock_gethostbyname):
    """Test the _is_public_url function with various scenarios."""
    # Public IP
    mock_gethostbyname.return_value = "8.8.8.8"
    assert _is_public_url("http://google.com") is True

    # Private IP
    mock_gethostbyname.return_value = "192.168.1.1"
    assert _is_public_url("http://private-router") is False

    # GAI error
    mock_gethostbyname.side_effect = socket.gaierror
    assert _is_public_url("http://invalid-host") is False

    # No hostname
    assert _is_public_url("/just/a/path") is False


def test_handle_add_source_invalid_url(capsys):
    """Test handle_add_source with an invalid URL format."""
    args = argparse.Namespace(url="not-a-url")
    handle_add_source(args)
    captured = capsys.readouterr()
    assert "Invalid URL format" in captured.out


def test_handle_remove_source_invalid_url(capsys):
    """Test handle_remove_source with an invalid URL format."""
    args = argparse.Namespace(url="not-a-url")
    handle_remove_source(args)
    captured = capsys.readouterr()
    assert "Invalid URL format" in captured.out


def test_handle_remove_source_normalized_no_path(sources_file: Path, capsys):
    """Test removing a URL with no path using a non-normalized equivalent."""
    url_to_remove = "HTTP://SOURCE1.COM#fragment"
    args = argparse.Namespace(sources_file=str(sources_file), url=url_to_remove)

    handle_remove_source(args)
    captured = capsys.readouterr()

    assert "Source removed: http://source1.com" in captured.out
    assert "http://source1.com" not in list_sources(sources_file)


def test_handle_remove_source_normalized_with_path(sources_file: Path, capsys):
    """Test removing a URL with a path using a non-normalized equivalent."""
    url_in_file = "http://source2.com/path"
    add_source(sources_file, url_in_file)

    url_to_remove = "HTTP://SOURCE2.COM/path?q=1#frag"
    args = argparse.Namespace(sources_file=str(sources_file), url=url_to_remove)

    handle_remove_source(args)
    captured = capsys.readouterr()

    assert f"Source removed: {url_in_file}" in captured.out
    assert url_in_file not in list_sources(sources_file)