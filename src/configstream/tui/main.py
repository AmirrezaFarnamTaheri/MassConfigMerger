"""Text-based User Interface for ConfigStream.

This module provides an interactive terminal interface using Rich.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()


class ConfigStreamTUI:
    """Interactive TUI for ConfigStream monitoring.

    Features:
    - Live updating node table
    - Statistics panel
    - Filter controls
    - Keyboard navigation

    Example:
        >>> tui = ConfigStreamTUI(data_dir=Path("./data"))
        >>> tui.run()
    """

    def __init__(self, data_dir: Path):
        """Initialize TUI.

        Args:
            data_dir: Directory containing test results
        """
        self.data_dir = data_dir
        self.current_file = data_dir / "current_results.json"
        self.running = False

        # Filter state
        self.filter_protocol = None
        self.filter_country = None
        self.show_only_successful = False

    def load_data(self) -> dict:
        """Load current test results."""
        if not self.current_file.exists():
            return {"nodes": [], "timestamp": None}

        try:
            return json.loads(self.current_file.read_text())
        except Exception:
            return {"nodes": [], "timestamp": None}

    def create_stats_panel(self, data: dict) -> Panel:
        """Create statistics panel.

        Args:
            data: Test results data

        Returns:
            Rich Panel with statistics
        """
        nodes = data.get("nodes", [])
        successful = len([n for n in nodes if n.get("ping_ms", 0) > 0])
        failed = len(nodes) - successful

        avg_ping = 0
        if successful > 0:
            avg_ping = (
                sum(n.get("ping_ms", 0) for n in nodes if n.get("ping_ms", 0) > 0)
                / successful
            )

        countries = len(set(n.get("country") for n in nodes))

        text = Text()
        text.append("Total Nodes: ", style="bold cyan")
        text.append(f"{len(nodes)}\n", style="bold white")

        text.append("Successful: ", style="bold green")
        text.append(f"{successful}\n", style="bold white")

        text.append("Failed: ", style="bold red")
        text.append(f"{failed}\n", style="bold white")

        text.append("Avg Ping: ", style="bold yellow")
        text.append(f"{avg_ping:.1f} ms\n", style="bold white")

        text.append("Countries: ", style="bold magenta")
        text.append(f"{countries}", style="bold white")

        return Panel(text, title="📊 Statistics", border_style="cyan", box=box.ROUNDED)

    def create_nodes_table(self, data: dict) -> Table:
        """Create nodes table.

        Args:
            data: Test results data

        Returns:
            Rich Table with node data
        """
        table = Table(
            title="🌐 VPN Nodes",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
        )

        table.add_column("Protocol", style="cyan", width=12)
        table.add_column("Country", style="blue", width=10)
        table.add_column("IP", style="white", width=15)
        table.add_column("Port", justify="right", width=7)
        table.add_column("Ping (ms)", justify="right", width=10)
        table.add_column("Status", width=10)

        nodes = data.get("nodes", [])

        # Apply filters
        if self.filter_protocol:
            nodes = [n for n in nodes if n.get("protocol") == self.filter_protocol]
        if self.filter_country:
            nodes = [n for n in nodes if n.get("country") == self.filter_country]
        if self.show_only_successful:
            nodes = [n for n in nodes if n.get("ping_ms", 0) > 0]

        # Sort by ping
        nodes = sorted(nodes, key=lambda n: n.get("ping_ms", 9999))

        # Show top 50 nodes
        for node in nodes[:50]:
            ping = node.get("ping_ms", 0)

            # Color code ping
            if ping < 0:
                ping_str = Text("Failed", style="bold red")
                status = "❌"
            elif ping < 100:
                ping_str = Text(f"{ping}", style="bold green")
                status = "✅"
            elif ping < 300:
                ping_str = Text(f"{ping}", style="bold yellow")
                status = "⚠️"
            else:
                ping_str = Text(f"{ping}", style="bold red")
                status = "🐌"

            table.add_row(
                node.get("protocol", ""),
                node.get("country", ""),
                node.get("ip", ""),
                str(node.get("port", "")),
                ping_str,
                status,
            )

        return table

    def create_filters_panel(self) -> Panel:
        """Create filters information panel.

        Returns:
            Rich Panel showing active filters
        """
        text = Text()
        text.append("Active Filters:\n\n", style="bold")

        if self.filter_protocol:
            text.append(f"Protocol: {self.filter_protocol}\n", style="cyan")

        if self.filter_country:
            text.append(f"Country: {self.filter_country}\n", style="blue")

        if self.show_only_successful:
            text.append("Only Successful\n", style="green")

        if not (
            self.filter_protocol or self.filter_country or self.show_only_successful
        ):
            text.append("None\n", style="dim")

        text.append("\nControls:\n", style="bold")
        text.append("q - Quit\n", style="dim")
        text.append("r - Refresh\n", style="dim")
        text.append("c - Clear filters\n", style="dim")

        return Panel(text, title="🔧 Controls", border_style="yellow", box=box.ROUNDED)

    def create_layout(self, data: dict) -> Layout:
        """Create main layout.

        Args:
            data: Test results data

        Returns:
            Rich Layout
        """
        layout = Layout()

        # Split into header and body
        layout.split(Layout(name="header", size=3), Layout(name="body"))

        # Split body into sidebar and main
        layout["body"].split_row(
            Layout(name="sidebar", ratio=1), Layout(name="main", ratio=3)
        )

        # Split sidebar into stats and filters
        layout["sidebar"].split(
            Layout(name="stats", ratio=1), Layout(name="filters", ratio=1)
        )

        # Populate layouts
        layout["header"].update(
            Panel("ConfigStream - VPN Node Monitor", style="bold white on blue")
        )

        layout["stats"].update(self.create_stats_panel(data))
        layout["filters"].update(self.create_filters_panel())
        layout["main"].update(self.create_nodes_table(data))

        return layout

    async def run_async(self):
        """Run TUI asynchronously with live updates."""
        self.running = True

        with Live(
            self.create_layout(self.load_data()), refresh_per_second=1, console=console
        ) as live:
            while self.running:
                try:
                    # Update display
                    data = self.load_data()
                    live.update(self.create_layout(data))

                    # Wait before next update
                    await asyncio.sleep(2)

                except KeyboardInterrupt:
                    self.running = False
                    break

    def run(self):
        """Run TUI (synchronous entry point)."""
        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            console.print("\n[bold red]Exiting...[/bold red]")


def launch_tui(data_dir: Path = Path("./data")):
    """Launch the TUI.

    Args:
        data_dir: Directory containing test results
    """
    tui = ConfigStreamTUI(data_dir)
    tui.run()
