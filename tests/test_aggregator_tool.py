import unittest
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from configstream.aggregator_tool import main as aggregator_main


class TestAggregatorTool(unittest.TestCase):
    @patch("configstream.cli.main")
    def test_main_redirects_to_cli_main(self, mock_cli_main: MagicMock):
        """
        Tests if the legacy aggregator tool correctly redirects to the main CLI
        with the appropriate arguments.
        """
        runner = CliRunner()
        result = runner.invoke(aggregator_main, [])

        self.assertEqual(result.exit_code, 0)
        mock_cli_main.assert_called_once_with(
            ["merge", "--sources", "sources.txt", "--output", "output/"]
        )

    @patch("configstream.cli.main")
    def test_main_with_legacy_flags(self, mock_cli_main: MagicMock):
        """
        Tests if the legacy aggregator tool ignores legacy flags and still
        redirects with the correct hardcoded arguments.
        """
        runner = CliRunner()
        result = runner.invoke(aggregator_main, ["--with-merger", "--hours", "48"])

        self.assertEqual(result.exit_code, 0)
        mock_cli_main.assert_called_once_with(
            ["merge", "--sources", "sources.txt", "--output", "output/"]
        )


if __name__ == "__main__":
    unittest.main()
