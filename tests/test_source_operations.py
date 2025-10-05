from __future__ import annotations

import argparse
import socket
from pathlib import Path
from unittest.mock import patch

from massconfigmerger.source_operations import (
    _is_public_url,
    add_source,
    handle_add_source,
    handle_list_sources,
    handle_remove_source,
    list_sources,
    remove_source,
)


def test_list_sources(fs):
    """Test listing sources from a file."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file, contents="http://a.com\nhttp://b.com\n")
    sources = list_sources(sources_file)
    assert sources == ["http://a.com", "http://b.com"]


def test_list_sources_file_not_found():
    """Test listing sources when the file does not exist."""
    sources_file = Path("nonexistent.txt")
    sources = list_sources(sources_file)
    assert sources == []


def test_add_source(fs):
    """Test adding a new source."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file)
    assert add_source(sources_file, "http://c.com")
    with open(sources_file) as f:
        assert "http://c.com" in f.read()


def test_add_duplicate_source(fs):
    """Test that adding a duplicate source returns False."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file, contents="http://a.com\n")
    assert not add_source(sources_file, "http://a.com")


def test_remove_source(fs):
    """Test removing an existing source."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file, contents="http://a.com\nhttp://b.com\n")
    assert remove_source(sources_file, "http://a.com")
    sources = list_sources(sources_file)
    assert "http://a.com" not in sources
    assert "http://b.com" in sources


def test_remove_nonexistent_source(fs):
    """Test that removing a non-existent source returns False."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file)
    assert not remove_source(sources_file, "http://nonexistent.com")


@patch("massconfigmerger.source_operations.socket.gethostbyname", side_effect=socket.gaierror)
def test_is_public_url_gaierror(mock_gethostbyname):
    """Test that _is_public_url handles socket.gaierror and returns False."""
    assert not _is_public_url("http://nonexistent-domain-xyz.com")


def test_handle_list_sources(fs, capsys):
    """Test the 'sources list' command handler."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file, contents="http://a.com\nhttp://b.com\n")
    args = argparse.Namespace(sources_file=str(sources_file))
    handle_list_sources(args)
    captured = capsys.readouterr()
    assert "http://a.com" in captured.out
    assert "http://b.com" in captured.out


def test_handle_list_sources_empty(fs, capsys):
    """Test the 'sources list' command with an empty sources file."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file)
    args = argparse.Namespace(sources_file=str(sources_file))
    handle_list_sources(args)
    captured = capsys.readouterr()
    assert "No sources found" in captured.out


@patch("massconfigmerger.source_operations._is_public_url", return_value=True)
def test_handle_add_source_success(mock_is_public, fs, capsys):
    """Test a successful source addition via the handler."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file)
    args = argparse.Namespace(sources_file=str(sources_file), url="http://example.com/new")
    handle_add_source(args)
    captured = capsys.readouterr()
    assert "Source added" in captured.out
    with open(sources_file) as f:
        assert "http://example.com/new" in f.read()


def test_handle_add_invalid_url(fs, capsys):
    """Test the 'sources add' command with an invalid URL."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file)
    args = argparse.Namespace(sources_file=str(sources_file), url="invalid-url")
    handle_add_source(args)
    captured = capsys.readouterr()
    assert "Invalid URL" in captured.out


@patch("massconfigmerger.source_operations._is_public_url", return_value=True)
def test_handle_add_duplicate(mock_is_public, fs, capsys):
    """Test the 'sources add' command with a duplicate URL."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file, contents="http://example.com/sub")
    args = argparse.Namespace(sources_file=str(sources_file), url="http://example.com/sub")
    handle_add_source(args)
    captured = capsys.readouterr()
    assert "Source already exists" in captured.out


@patch("massconfigmerger.source_operations._is_public_url", return_value=False)
def test_handle_add_source_not_public(mock_is_public, fs, capsys):
    """Test adding a source that is not a public URL."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file)
    args = argparse.Namespace(sources_file=str(sources_file), url="http://127.0.0.1/sub")
    handle_add_source(args)
    captured = capsys.readouterr()
    assert "URL does not point to a public IP address" in captured.out


def test_handle_remove_source_success(fs, capsys):
    """Test a successful source removal via the handler."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file, contents="http://example.com/to-remove\n")
    args = argparse.Namespace(sources_file=str(sources_file), url="http://example.com/to-remove")
    handle_remove_source(args)
    captured = capsys.readouterr()
    assert "Source removed: http://example.com/to-remove" in captured.out
    with open(sources_file) as f:
        assert "http://example.com/to-remove" not in f.read()


def test_handle_remove_not_found(fs, capsys):
    """Test the 'sources remove' command when the source is not found."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file)
    args = argparse.Namespace(sources_file=str(sources_file), url="http://example.com/sub")
    handle_remove_source(args)
    captured = capsys.readouterr()
    assert "Source not found" in captured.out


def test_handle_remove_invalid_url(fs, capsys):
    """Test removing a source with an invalid URL."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file)
    args = argparse.Namespace(sources_file=str(sources_file), url="not-a-url")
    handle_remove_source(args)
    captured = capsys.readouterr()
    assert "Invalid URL format" in captured.out


def test_handle_remove_source_normalized(fs, capsys):
    """Test that source removal is case-insensitive and ignores fragments."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file, contents="http://example.com/path\n")
    url_to_remove = "HTTP://EXAMPLE.com/path?query#fragment"
    args = argparse.Namespace(sources_file=str(sources_file), url=url_to_remove)
    handle_remove_source(args)
    captured = capsys.readouterr()
    assert "Source removed: http://example.com/path" in captured.out
    assert not list_sources(sources_file)


def test_handle_remove_source_normalized_no_path(fs, capsys):
    """Test normalization of a URL with no path."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file, contents="http://example.com\n")
    url_to_remove = "HTTP://EXAMPLE.com"
    args = argparse.Namespace(sources_file=str(sources_file), url=url_to_remove)
    handle_remove_source(args)
    captured = capsys.readouterr()
    assert "Source removed: http://example.com" in captured.out
    assert not list_sources(sources_file)