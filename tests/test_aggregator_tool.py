import subprocess
from unittest.mock import patch

from click.testing import CliRunner

from configstream.aggregator_tool import main as aggregator_main


def test_main_redirects_to_cli_main():
    """
    Tests if the legacy aggregator tool correctly calls the main CLI.
    """
    runner = CliRunner()
    with patch("subprocess.run") as mock_subprocess_run:
        result = runner.invoke(aggregator_main, [])
        assert result.exit_code == 0
        assert "Legacy aggregator_tool is deprecated" in result.output
        mock_subprocess_run.assert_called_once_with([
            "configstream", "merge", "--sources", "sources.txt", "--output",
            "output/"
        ],
            check=True)


def test_main_handles_file_not_found():
    """
    Tests if the tool exits gracefully if the command is not found.
    """
    runner = CliRunner()
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = runner.invoke(aggregator_main, [])
        assert result.exit_code == 1
        assert "Error: The command 'configstream' was not found." in result.output


def test_main_handles_called_process_error():
    """
    Tests if the tool exits gracefully on a subprocess error.
    """
    runner = CliRunner()
    with patch("subprocess.run",
               side_effect=subprocess.CalledProcessError(returncode=1,
                                                         cmd="...")):
        result = runner.invoke(aggregator_main, [])
        assert result.exit_code == 1
        assert "The command failed with exit code 1" in result.output
