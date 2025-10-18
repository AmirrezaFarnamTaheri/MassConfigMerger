import pytest
from click.testing import CliRunner
from unittest.mock import patch
from configstream.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_merge_nonexistent_sources(runner):
    """Test the merge command with a non-existent sources file."""
    result = runner.invoke(
        cli, ["merge", "--sources", "no_such_file.txt", "--output", "output/"])
    assert result.exit_code == 2  # click's error code for bad parameter
    assert "does not exist" in result.output


def test_cli_merge_empty_sources(runner, tmp_path):
    """Test the merge command with an empty sources file."""
    sources_file = tmp_path / "empty_sources.txt"
    sources_file.write_text("")
    result = runner.invoke(
        cli, ["merge", "--sources",
              str(sources_file), "--output", "output/"])
    assert result.exit_code == 1
    assert "No sources found" in result.output


def test_update_databases_failure(runner, mocker):
    """Test the update-databases command when the download fails."""
    mocker.patch("configstream.geoip.download_geoip_dbs", return_value=False)
    result = runner.invoke(cli, ["update-databases"])
    assert result.exit_code == 0  # Command itself doesn't fail
    assert "Some databases failed to update" in result.output


def test_retest_nonexistent_input(runner):
    """Test the retest command with a non-existent input file."""
    result = runner.invoke(
        cli, ["retest", "--input", "no_such_file.json", "--output", "output/"])
    assert result.exit_code == 2
    assert "does not exist" in result.output


def test_retest_empty_input(runner, tmp_path):
    """Test the retest command with an empty input file."""
    input_file = tmp_path / "empty.json"
    input_file.write_text("[]")
    result = runner.invoke(
        cli, ["retest", "--input",
              str(input_file), "--output", "output/"])
    assert result.exit_code == 1
    assert "No proxies found" in result.output


def test_retest_invalid_json(runner, tmp_path):
    """Test the retest command with invalid JSON."""
    input_file = tmp_path / "invalid.json"
    input_file.write_text("[{]")
    result = runner.invoke(
        cli, ["retest", "--input",
              str(input_file), "--output", "output/"])
    assert result.exit_code == 1
    assert "An error occurred: Expecting property name" in result.output


def test_cli_merge_max_proxies(runner):
    """Test the --max-proxies option."""
    with runner.isolated_filesystem():
        with open("sources.txt", "w") as f:
            f.write("http://example.com")
        with patch("configstream.cli.download_geoip_dbs"), patch(
                "configstream.cli.pipeline.run_full_pipeline"
        ) as mock_pipeline:
            result = runner.invoke(
                cli,
                ["merge", "--sources", "sources.txt", "--max-proxies", "50"])
            assert result.exit_code == 0, result.output
            # Check that the max_proxies argument was passed to the pipeline
            assert mock_pipeline.call_args.kwargs["max_proxies"] == 50


def test_cli_merge_latency_filters(runner):
    """Test the --min-latency and --max-latency options."""
    with runner.isolated_filesystem():
        with open("sources.txt", "w") as f:
            f.write("http://example.com")
        with patch("configstream.cli.download_geoip_dbs"), patch(
                "configstream.cli.pipeline.run_full_pipeline"
        ) as mock_pipeline:
            result = runner.invoke(
                cli,
                [
                    "merge",
                    "--sources",
                    "sources.txt",
                    "--min-latency",
                    "10",
                    "--max-latency",
                    "200",
                ],
            )
            assert result.exit_code == 0, result.output
            # Check that latency filters were passed to the pipeline
            assert mock_pipeline.call_args.kwargs["min_latency"] == 10
            assert mock_pipeline.call_args.kwargs["max_latency"] == 200


def test_cli_merge_country_filter(runner):
    """Test the --country option."""
    with runner.isolated_filesystem():
        with open("sources.txt", "w") as f:
            f.write("http://example.com")
        with patch("configstream.cli.download_geoip_dbs"), patch(
                "configstream.cli.pipeline.run_full_pipeline"
        ) as mock_pipeline:
            result = runner.invoke(
                cli, ["merge", "--sources", "sources.txt", "--country", "US"])
            assert result.exit_code == 0, result.output
            # Check that the country filter was passed to the pipeline
            assert mock_pipeline.call_args.kwargs["country_filter"] == "US"


def test_cli_merge_sources_file_not_found(runner):
    """Test the merge command when the sources file does not exist."""
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["merge", "--sources", "nonexistent.txt"])
        assert result.exit_code != 0
        assert "File 'nonexistent.txt' does not exist" in result.output


def test_cli_retest_input_file_not_found(runner):
    """Test the retest command when the input file does not exist."""
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["retest", "--input", "nonexistent.json"])
        assert result.exit_code != 0
        assert "File 'nonexistent.json' does not exist" in result.output


def test_cli_update_databases(runner):
    """Test the update-databases command."""
    with patch("configstream.cli.download_geoip_dbs") as mock_download:
        result = runner.invoke(cli, ["update-databases"])
        assert result.exit_code == 0
        mock_download.assert_called_once()
