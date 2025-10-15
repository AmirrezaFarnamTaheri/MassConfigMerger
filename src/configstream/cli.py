from __future__ import annotations

import click

from . import generator, tester
from .config import settings
from .fetcher import fetch_all


@click.group()
def cli():
    """
    Automated Free VPN Configuration Aggregator.
    """
    pass


@click.command("fetch")
def fetch_command():
    """
    Fetch configurations from sources.
    """
    click.echo("Fetching configurations...")
    configs = fetch_all(settings.sources)
    click.echo(f"Fetched {len(configs)} configurations.")
    # For now, we'll just print them
    for config in configs:
        click.echo(config)


@click.command("test")
def test_command():
    """
    Test existing configurations.
    """
    click.echo("Testing configurations...")
    # This is a placeholder
    results = tester.test_configs([])
    click.echo(f"Tested {len(results)} configurations.")


@click.command("generate")
def generate_command():
    """
    Generate output files.
    """
    click.echo("Generating output files...")
    # This is a placeholder
    generator.generate_files([], settings.output_dir)
    click.echo("Output files generated.")


@click.command("full")
def full_command():
    """
    Run the full pipeline: fetch, test, and generate.
    """
    click.echo("Running full pipeline...")
    click.echo("Step 1: Fetching configurations...")
    configs = fetch_all(settings.sources)
    click.echo(f"Fetched {len(configs)} configurations.")

    click.echo("Step 2: Testing configurations...")
    results = tester.test_configs(configs)
    click.echo(f"Tested {len(results)} configurations.")

    click.echo("Step 3: Generating output files...")
    generator.generate_files(results, settings.output_dir)
    click.echo("Full pipeline complete.")


cli.add_command(fetch_command)
cli.add_command(test_command)
cli.add_command(generate_command)
cli.add_command(full_command)

if __name__ == "__main__":
    cli()