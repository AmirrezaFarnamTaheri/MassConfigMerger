import pytest
import json
from pathlib import Path
from unittest.mock import patch, call

from configstream.tui import display_results


@patch("configstream.tui.Table")
@patch("configstream.tui.Console")
def test_display_results_table(mock_console_cls, mock_table_cls, fs):
    """Test that display_results prints a table with the correct data."""
    # Arrange
    mock_console = mock_console_cls.return_value
    mock_table = mock_table_cls.return_value
    results_data = {
        "nodes": [
            {
                "protocol": "VLESS",
                "country": "US",
                "ping_ms": 120,
                "organization": "Test Org",
                "ip": "1.1.1.1",
                "port": 443,
            },
            {
                "protocol": "SS",
                "country": "DE",
                "ping_ms": -1,
                "organization": "Another Org",
                "ip": "8.8.8.8",
                "port": 80,
            },
        ]
    }
    results_file = Path("/fake_results.json")
    results_file.write_text(json.dumps(results_data))

    # Act
    display_results(results_file)

    # Assert
    mock_table_cls.assert_called_once_with(show_header=True, header_style="bold magenta")

    # Check that columns were added
    add_column_calls = [
        call("Protocol", style="dim", width=12),
        call("Country"),
        call("Ping (ms)"),
        call("Organization"),
        call("IP:Port"),
    ]
    mock_table.add_column.assert_has_calls(add_column_calls, any_order=False)

    # Check that rows were added
    add_row_calls = [
        call("VLESS", "US", "[green]120[/green]", "Test Org", "1.1.1.1:443"),
        call("SS", "DE", "[red]Failed[/red]", "Another Org", "8.8.8.8:80"),
    ]
    mock_table.add_row.assert_has_calls(add_row_calls, any_order=False)

    # Check that the table was printed
    mock_console.print.assert_called_once_with(mock_table)


def test_display_results_file_not_found(capsys, fs):
    """Test that a message is printed when the results file is not found."""
    results_file = Path("/non_existent_file.json")

    display_results(results_file)

    captured = capsys.readouterr()
    assert "Results file not found" in captured.out