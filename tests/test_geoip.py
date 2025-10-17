import io
import os
import tarfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from configstream.geoip import GeoIPManager, download_geoip_dbs


@pytest.fixture
def manager(fs):
    """Fixture for GeoIPManager with a fake filesystem."""
    # fs is the pyfakefs fixture, it will automatically handle the directory creation
    return GeoIPManager(license_key="test_key")


def test_init_with_license_key():
    manager = GeoIPManager(license_key="test_key")
    assert manager.license_key == "test_key"


@patch.dict(os.environ, {"MAXMIND_LICENSE_KEY": "env_key"})
def test_init_with_env_variable():
    manager = GeoIPManager()
    assert manager.license_key == "env_key"


def test_init_no_license_key():
    manager = GeoIPManager()
    assert manager.license_key is None


@pytest.mark.asyncio
async def test_download_databases_no_key():
    manager = GeoIPManager()
    manager.license_key = None
    result = await manager.download_databases()
    assert not result


@pytest.mark.asyncio
@patch("aiohttp.ClientSession")
async def test_download_databases_success(mock_session, manager):
    manager._download_and_extract = AsyncMock()
    result = await manager.download_databases()
    assert result
    assert manager._download_and_extract.call_count == 2


@pytest.mark.asyncio
@patch("aiohttp.ClientSession")
async def test_download_databases_failure(mock_session, manager):
    manager._download_and_extract = AsyncMock(side_effect=Exception("Download failed"))
    result = await manager.download_databases()
    assert not result


@pytest.mark.asyncio
async def test_download_and_extract(manager, fs):
    # Create a mock tar.gz file in memory
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        db_content = b"dummy_db_content"
        tarinfo = tarfile.TarInfo(name="GeoLite2-City_20240101/GeoLite2-City.mmdb")
        tarinfo.size = len(db_content)
        tar.addfile(tarinfo, io.BytesIO(db_content))
    tar_buffer.seek(0)

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.read.return_value = tar_buffer.read()

    # session.get() returns an async context manager.
    get_context_manager = AsyncMock()
    get_context_manager.__aenter__.return_value = mock_response

    # session.get is a regular method, so we use MagicMock for it.
    mock_session = MagicMock()
    mock_session.get.return_value = get_context_manager

    await manager._download_and_extract(mock_session, "http://fake-url.com", "city")

    db_path = Path("data") / "GeoLite2-City.mmdb"
    assert db_path.exists()
    assert db_path.read_bytes() == b"dummy_db_content"

    # Check that the tar file is cleaned up
    tar_path = Path("data") / "geoip-city.tar.gz"
    assert not tar_path.exists()


def test_verify_databases_success(manager, fs):
    fs.create_file("data/GeoLite2-Country.mmdb", contents="country_data")
    fs.create_file("data/GeoLite2-City.mmdb", contents="city_data")
    assert manager.verify_databases()


def test_verify_databases_failure(manager):
    assert not manager.verify_databases()


@pytest.mark.asyncio
@patch("configstream.geoip.GeoIPManager")
async def test_download_geoip_dbs_success(mock_manager_class):
    mock_manager = mock_manager_class.return_value
    mock_manager.download_databases = AsyncMock(return_value=True)
    mock_manager.verify_databases = MagicMock(return_value=True)

    result = await download_geoip_dbs()

    assert result
    mock_manager.download_databases.assert_called_once()
    mock_manager.verify_databases.assert_called_once()


@pytest.mark.asyncio
@patch("configstream.geoip.GeoIPManager")
async def test_download_geoip_dbs_failure(mock_manager_class):
    mock_manager = mock_manager_class.return_value
    mock_manager.download_databases = AsyncMock(return_value=False)

    result = await download_geoip_dbs()

    assert not result
    mock_manager.download_databases.assert_called_once()
    mock_manager.verify_databases.assert_not_called()
