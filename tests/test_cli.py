import json
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from configstream.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_merge_command(runner):
    result = runner.invoke(
        cli, ["merge", "--sources", "sources.mini.txt", "--output", "output/"])
    assert result.exit_code == 0
    assert "Pipeline completed successfully!" in result.output


def test_cli_retest_command(runner, mocker):
    valid_proxy = {
        "config": "vmess://test",
        "protocol": "vmess",
        "address": "test.com",
        "port": 443,
        "uuid": "test-uuid",
        "remarks": "test-remark",
        "country": "US",
        "country_code": "US",
        "city": "New York",
        "asn": "AS12345",
        "latency": 100.0,
        "is_working": True,
        "is_secure": True,
        "security_issues": [],
        "tested_at": "2024-01-01T00:00:00Z",
        "details": {},
    }
    mocker.patch("builtins.open",
                 mocker.mock_open(read_data=json.dumps([valid_proxy])))
    mocker.patch(
        "configstream.pipeline.run_full_pipeline",
        new_callable=AsyncMock,
        return_value={
            "success": True,
            "stats": {},
            "output_files": {},
            "error": None
            },
        )
    result = runner.invoke(
        cli,
        ["retest", "--input", "output/proxies.json", "--output", "output/"])
    assert result.exit_code == 0
    assert "Retest completed successfully!" in result.output


def test_cli_update_databases_command(runner, mocker):
    mocker.patch("asyncio.run", return_value=True)
    result = runner.invoke(cli, ["update-databases"])
    assert result.exit_code == 0
    assert "All databases updated successfully!" in result.output


def test_cli_merge_command_with_no_sources(runner):
    result = runner.invoke(cli, ["merge", "--output", "output/"])
    assert result.exit_code != 0
    assert "Error: Missing option '--sources'" in result.output


def test_cli_merge_command_with_no_output(runner):
    result = runner.invoke(cli, ["merge", "--sources", "sources.mini.txt"])
    assert result.exit_code == 0
    assert "Pipeline completed successfully!" in result.output


def test_cli_retest_command_with_no_input(runner):
    result = runner.invoke(cli, ["retest", "--output", "output/"])
    assert result.exit_code != 0
    assert "No proxies found" in result.output
