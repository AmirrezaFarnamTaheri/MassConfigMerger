from pathlib import Path
import pytest
from massconfigmerger.source_operations import (
    list_sources,
    add_source,
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