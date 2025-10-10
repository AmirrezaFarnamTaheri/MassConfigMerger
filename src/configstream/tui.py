# ConfigStream
# Copyright (C) 2025 Amirreza "Farnam" Taheri
# This program comes with ABSOLUTELY NO WARRANTY; for details type `show w`.
# This is free software, and you are welcome to redistribute it
# under certain conditions; type `show c` for details.
# For more information, see <https://amirrezafarnamtaheri.github.io/configStream/>.

"""Terminal user interface for displaying test results."""
from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.table import Table


def display_results(results_file: Path):
    """Display test results in a table."""
    if not results_file.exists():
        print(f"Results file not found: {results_file}")
        return

    console = Console()
    data = json.loads(results_file.read_text())
    nodes = data.get("nodes", [])

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Protocol", style="dim", width=12)
    table.add_column("Country")
    table.add_column("Ping (ms)")
    table.add_column("Organization")
    table.add_column("IP:Port")

    for node in nodes:
        ping = node.get("ping_ms", -1)
        ping_str = f"[green]{ping}[/green]" if ping > 0 else "[red]Failed[/red]"
        table.add_row(
            node.get("protocol", "N/A"),
            node.get("country", "N/A"),
            ping_str,
            node.get("organization", "N/A"),
            f"{node.get('ip', 'N/A')}:{node.get('port', 'N/A')}",
        )

    console.print(table)