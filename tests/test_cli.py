from __future__ import annotations

import gzip
from unittest.mock import patch

from click.testing import CliRunner

from configstream.cli import download_geoip_dbs, main

# --- Test Data ---

FAKE_DB_CONTENT = b"fake geoip database content"
GZIPPED_FAKE_DB_CONTENT = gzip.compress(FAKE_DB_CONTENT)

# --- Tests ---


def test_download_geoip_dbs_exists(fs):
    """
    Tests that the download function does nothing if the DBs already exist.
    """
    # Create fake existing database files
    fs.create_file("data/GeoLite2-Country.mmdb", contents="exists")
    fs.create_file("data/GeoLite2-City.mmdb", contents="exists")
    fs.create_file("data/ip-to-asn.mmdb", contents="exists")

    with patch("requests.get") as mock_get:
        download_geoip_dbs()
        mock_get.assert_not_called()


def test_download_geoip_dbs_success(fs):
    """
    Tests the successful download and extraction of the GeoIP databases.
    """
    # Ensure the target directory does not exist initially
    assert not fs.exists("data")

    with patch("requests.get") as mock_get:
        # Mock the response from requests.get
        mock_response = mock_get.return_value.__enter__.return_value
        mock_response.iter_content.return_value = [GZIPPED_FAKE_DB_CONTENT]
        mock_response.raise_for_status.return_value = None

        download_geoip_dbs()

        # Verify the files were created and have the correct content
        assert fs.exists("data/GeoLite2-Country.mmdb")
        with open("data/GeoLite2-Country.mmdb", "rb") as f:
            assert f.read() == FAKE_DB_CONTENT
        assert fs.exists("data/ip-to-asn.mmdb")

        # Verify the temporary .gz file was removed
        assert not fs.exists("data/GeoLite2-Country.mmdb.gz")


def test_cli_merge_command(fs):
    """
    A simple test for the merge command to ensure it runs without crashing.
    """
    # Create a fake sources file
    fs.create_file("sources.txt", contents="https://example.com/source1")

    runner = CliRunner()
    # We patch the pipeline and download_geoip_dbs to avoid external dependencies
    with patch("configstream.cli.pipeline.run_full_pipeline") as mock_pipeline, \
         patch("configstream.cli.download_geoip_dbs") as mock_download:
        result = runner.invoke(main, ["merge", "--sources", "sources.txt"])

        assert result.exit_code == 0
        mock_download.assert_called_once()
        mock_pipeline.assert_called_once()
