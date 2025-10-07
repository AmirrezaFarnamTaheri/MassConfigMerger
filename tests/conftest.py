"""Pytest configuration and shared fixtures."""

import asyncio
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

import importlib
import importlib.util

import pytest

from configstream.config import Settings


def _load_optional_plugin(name: str) -> str | None:
    """Try to load an optional pytest plugin.

    When running in the execution environment used for these kata style tasks the
    optional test dependencies are often not installed. Importing a missing
    plugin would therefore raise an exception during pytest collection and no
    tests would be executed.  To keep the suite runnable we attempt the import
    dynamically and only register the plugin when it is available locally.
    """

    if importlib.util.find_spec(name) is None:
        return None
    importlib.import_module(name)
    return name


# Ensure optional pytest plugins are loaded when available without failing when
# they are missing from the execution environment.
pytest_plugins = [
    plugin
    for plugin in (
        _load_optional_plugin("pytest_asyncio"),
        _load_optional_plugin("aiohttp.pytest_plugin"),
    )
    if plugin is not None
]


def pytest_addoption(parser):
    """Register compatibility ini options when pytest-asyncio is unavailable."""

    parser.addini("asyncio_mode", "Compatibility shim for pytest-asyncio", default="auto")


# Do not use proxies when running tests to avoid network issues with local
# test servers.
CONFIG = Settings()
CONFIG.network.http_proxy = None
CONFIG.network.socks_proxy = None

@pytest.fixture
def loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def event_loop(loop):
    yield loop


class SimpleFakeFilesystem:
    """Minimal stand-in for pyfakefs when the plugin is unavailable."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self._created_dirs: set[Path] = set()
        self._created_files: set[Path] = set()

    def _real_path(self, path: Path | str) -> Path:
        path_obj = Path(path)
        if path_obj.is_absolute():
            return path_obj
        return self.root.joinpath(path_obj)

    def create_dir(self, path: Path | str) -> Path:
        real_path = self._real_path(path)
        if not real_path.exists():
            real_path.mkdir(parents=True, exist_ok=True)
            self._created_dirs.add(real_path)
        return real_path

    def create_file(self, path: Path | str, contents: str | bytes | bytearray | None = "") -> Path:
        real_path = self._real_path(path)
        real_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(contents, (bytes, bytearray)):
            real_path.write_bytes(bytes(contents))
        else:
            real_path.write_text(contents or "")
        self._created_files.add(real_path)
        return real_path

    def cleanup(self) -> None:
        for file_path in sorted(self._created_files, key=lambda p: len(p.parts), reverse=True):
            try:
                file_path.unlink(missing_ok=True)
            except OSError:
                pass
        for dir_path in sorted(self._created_dirs, key=lambda p: len(p.parts), reverse=True):
            try:
                shutil.rmtree(dir_path, ignore_errors=True)
            except OSError:
                pass


@pytest.fixture
def fs(tmp_path):
    """Provide a lightweight filesystem helper compatible with pyfakefs tests."""

    original_cwd = Path.cwd()
    fake_root = tmp_path / "fs"
    fake_root.mkdir()
    os.chdir(fake_root)
    fs_helper = SimpleFakeFilesystem(fake_root)
    try:
        yield fs_helper
    finally:
        fs_helper.cleanup()
        os.chdir(original_cwd)
