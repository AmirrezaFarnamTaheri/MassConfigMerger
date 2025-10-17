from __future__ import annotations

import json
from unittest.mock import patch

from click.testing import CliRunner

from configstream.cli import main


@patch("configstream.cli.download_geoip_dbs")
def test_merge_command_happy_path(mock_download_dbs, fs):
    """
    Tests the merge command with a mock pipeline and fake file system.
    """
    # Create a fake sources file
    fs.create_file("sources.txt", contents="http://source1.com\nhttp://source2.com")

    # Mock the pipeline function
    with patch("configstream.pipeline.run_full_pipeline") as mock_run_pipeline:
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "merge",
                "--sources",
                "sources.txt",
                "--output",
                "output_dir",
                "--max-proxies",
                "100",
                "--country",
                "US",
                "--max-latency",
                "500",
            ],
        )

        assert result.exit_code == 0
        assert "Pipeline completed successfully!" in result.output
        mock_run_pipeline.assert_called_once()
        mock_download_dbs.assert_called_once()


def test_merge_command_no_sources_file():
    """
    Tests the merge command when the sources file does not exist.
    """
    runner = CliRunner()
    result = runner.invoke(main, ["merge", "--sources", "nonexistent.txt"])

    assert result.exit_code != 0
    assert "File 'nonexistent.txt' does not exist" in result.output


@patch("configstream.cli.download_geoip_dbs")
def test_update_databases_command(mock_download_dbs, fs):
    """
    Tests the update-databases command with a fake file system.
    """
    # Create fake existing databases
    fs.create_file("data/GeoLite2-Country.mmdb")
    fs.create_file("data/GeoLite2-City.mmdb")

    runner = CliRunner()
    result = runner.invoke(main, ["update-databases"])

    assert result.exit_code == 0
    assert "All databases updated successfully!" in result.output
    mock_download_dbs.assert_called_once()


@patch("configstream.pipeline.run_full_pipeline")
def test_retest_command_happy_path(mock_run_pipeline, fs):
    """
    Tests the retest command with a mock pipeline and fake file system.
    """
    # Create a fake proxies file
    proxies_data = [
        {
            "config": "vmess://test1",
            "protocol": "vmess",
            "address": "1.1.1.1",
            "port": 443,
            "latency": 100,
            "country_code": "US",
            "remarks": "test1",
        }
    ]
    fs.create_file("output/proxies.json", contents=json.dumps(proxies_data))

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "retest",
            "--input",
            "output/proxies.json",
            "--output",
            "output_dir",
        ],
    )

    assert result.exit_code == 0
    assert "Retest completed successfully!" in result.output
    mock_run_pipeline.assert_called_once()
