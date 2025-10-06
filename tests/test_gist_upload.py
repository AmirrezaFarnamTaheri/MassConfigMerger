import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from massconfigmerger.exceptions import ConfigError, GistUploadError
from massconfigmerger.gist_uploader import (
    upload_files_to_gist,
    write_upload_links,
)


@pytest.mark.asyncio
@patch("massconfigmerger.gist_uploader.aiohttp.ClientSession")
async def test_upload_files_to_gist_success(MockSession, tmp_path: Path):
    """Test successful Gist upload using a mocked session."""
    f = tmp_path / "vpn_subscription_raw.txt"
    f.write_text("data", encoding="utf-8")

    # Mock the response object that will be yielded by the context manager
    mock_resp = AsyncMock()
    mock_resp.status = 201
    mock_resp.json = AsyncMock(
        return_value={"files": {f.name: {"raw_url": f"https://gist.github.com/raw/{f.name}"}}}
    )

    # Mock the async context manager that session.post() returns
    mock_post_cm = AsyncMock()
    mock_post_cm.__aenter__.return_value = mock_resp

    # Mock the session object
    mock_session = MockSession.return_value.__aenter__.return_value
    # session.post is a regular method that returns an async context manager
    mock_session.post = MagicMock(return_value=mock_post_cm)

    # Call the function under test
    links = await upload_files_to_gist([f], "secret")

    # Assertions
    mock_session.post.assert_called_once()
    pos_args, kw_args = mock_session.post.call_args
    assert pos_args[0] == "https://api.github.com/gists"
    assert kw_args["json"]["files"][f.name]["content"] == "data"
    assert links == {f.name: f"https://gist.github.com/raw/{f.name}"}

    path = write_upload_links(links, tmp_path)
    assert path.read_text().strip() == f"{f.name}: https://gist.github.com/raw/{f.name}"


@pytest.mark.asyncio
@patch("massconfigmerger.gist_uploader.aiohttp.ClientSession")
async def test_upload_files_to_gist_failure(MockSession, tmp_path: Path):
    """Test Gist upload failure handling."""
    f = tmp_path / "vpn_subscription_raw.txt"
    f.write_text("data", encoding="utf-8")

    # Mock the response object
    mock_resp = AsyncMock()
    mock_resp.status = 400
    mock_resp.text = AsyncMock(return_value="Bad Request")

    # Mock the async context manager
    mock_post_cm = AsyncMock()
    mock_post_cm.__aenter__.return_value = mock_resp

    # Mock the session object
    mock_session = MockSession.return_value.__aenter__.return_value
    mock_session.post = MagicMock(return_value=mock_post_cm)

    # Assert that the correct exception is raised
    with pytest.raises(GistUploadError, match=r"Gist upload failed for .*: 400 Bad Request"):
        await upload_files_to_gist([f], "secret")


@pytest.mark.asyncio
async def test_upload_files_to_gist_no_token():
    """Test that a ValueError is raised if no token is provided."""
    with pytest.raises(ConfigError, match="GitHub token is required"):
        await upload_files_to_gist([], "")


@pytest.mark.asyncio
async def test_upload_files_to_gist_invalid_base_url():
    """Test that a ValueError is raised for an invalid base_url."""
    with pytest.raises(ConfigError, match="Invalid base_url"):
        await upload_files_to_gist([], "secret", base_url="ftp://invalid.com")


@pytest.mark.asyncio
async def test_upload_files_to_gist_file_not_found(tmp_path: Path):
    """Test that an error is raised if a file does not exist."""
    non_existent_file = tmp_path / "non_existent.txt"
    with pytest.raises(GistUploadError, match="Gist upload source is not a file"):
        await upload_files_to_gist([non_existent_file], "secret")


@pytest.mark.asyncio
@patch("massconfigmerger.gist_uploader.aiohttp.ClientSession")
async def test_upload_files_to_gist_invalid_json_response(MockSession, tmp_path: Path):
    """Test Gist upload with a non-JSON response."""
    f = tmp_path / "test.txt"
    f.write_text("data")

    mock_resp = AsyncMock()
    mock_resp.status = 201
    mock_resp.json = AsyncMock(side_effect=asyncio.TimeoutError)  # Simulate JSON parsing failure
    mock_resp.text = AsyncMock(return_value="not json")

    mock_post_cm = AsyncMock()
    mock_post_cm.__aenter__.return_value = mock_resp

    mock_session = MockSession.return_value.__aenter__.return_value
    mock_session.post = MagicMock(return_value=mock_post_cm)

    with pytest.raises(GistUploadError, match="Failed to parse Gist response"):
        await upload_files_to_gist([f], "secret")


@pytest.mark.asyncio
@patch("massconfigmerger.gist_uploader.aiohttp.ClientSession")
async def test_upload_files_to_gist_unexpected_json_structure(MockSession, tmp_path: Path):
    """Test Gist upload with an unexpected JSON structure in the response."""
    f = tmp_path / "test.txt"
    f.write_text("data")

    mock_resp = AsyncMock()
    mock_resp.status = 201
    mock_resp.json = AsyncMock(return_value={"files": {"wrong_name": {}}})  # Missing raw_url key

    mock_post_cm = AsyncMock()
    mock_post_cm.__aenter__.return_value = mock_resp

    mock_session = MockSession.return_value.__aenter__.return_value
    mock_session.post = MagicMock(return_value=mock_post_cm)

    with pytest.raises(GistUploadError, match="Unexpected Gist response"):
        await upload_files_to_gist([f], "secret")