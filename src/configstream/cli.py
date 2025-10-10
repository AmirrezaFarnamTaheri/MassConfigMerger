"""Command-line interface for ConfigStream.

This module provides the main entry point for the `configstream` command-line
tool. It uses `argparse` to define a set of subcommands (`fetch`, `merge`,
`retest`, `full`) and their corresponding arguments. The CLI is responsible for
parsing user input, loading the application configuration, overriding settings
with command-line arguments, and dispatching to the appropriate handler function
for the selected command.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, Dict

from pydantic import BaseModel

from . import cli_args, commands, services
from .config import Settings, load_config
from .constants import CONFIG_FILE_NAME
from .core.utils import print_public_source_warning


def build_parser() -> argparse.ArgumentParser:
    """Build the main `argparse` parser with all subcommands and arguments."""
    parser = argparse.ArgumentParser(
        prog="configstream", description="A tool for collecting and merging VPN configurations."
    )
    parser.add_argument(
        "--config", default=CONFIG_FILE_NAME, help=f"Path to {CONFIG_FILE_NAME}"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Fetch command
    fetch_p = subparsers.add_parser(
        "fetch", help="Run the aggregation pipeline")
    cli_args.add_fetch_arguments(fetch_p)

    # Merge command
    merge_p = subparsers.add_parser("merge", help="Run the VPN merger")
    cli_args.add_merge_arguments(merge_p)

    # Retest command
    retest_p = subparsers.add_parser(
        "retest", help="Retest an existing subscription")
    cli_args.add_retest_arguments(retest_p)

    # Full command
    full_p = subparsers.add_parser(
        "full", help="Aggregate, then merge and test configurations"
    )
    cli_args.add_full_arguments(full_p)

    # Sources command
    cli_args.add_sources_parser(subparsers)

    # Daemon command
    daemon_p = subparsers.add_parser(
        "daemon", help="Run the scheduler and web dashboard"
    )
    cli_args.add_daemon_arguments(daemon_p)

    # TUI command
    cli_args.add_tui_arguments(subparsers)

    return parser


def _parse_protocol_list(value: str | list[str] | None) -> list[str]:
    """Parse a comma-separated string of protocols into a list of uppercase strings."""
    if not value:
        return []
    if isinstance(value, str):
        return [v.strip().upper() for v in value.split(",") if v.strip()]
    return [v.strip().upper() for v in value]


def _parse_protocol_set(value: str | list[str] | None) -> set[str]:
    """Parse a comma-separated string of protocols into a set of uppercase strings."""
    if not value:
        return set()
    if isinstance(value, str):
        return {v.strip().upper() for v in value.split(",") if v.strip()}
    return {v.strip().upper() for v in value}


def _update_settings_from_args(cfg: Settings, args: argparse.Namespace):
    """Update the `Settings` object with values from parsed CLI arguments."""
    arg_dict = {k: v for k, v in vars(args).items() if v is not None}

    # Arguments that are lists and need to be extended
    list_extend_fields = {"include_patterns", "exclude_patterns"}

    for group_name, _ in Settings.model_fields.items():
        if not hasattr(cfg, group_name):
            continue

        group = getattr(cfg, group_name)
        if not isinstance(group, BaseModel):
            continue

        for field_name in group.__class__.model_fields:
            if field_name in arg_dict:
                value = arg_dict[field_name]

                if field_name in list_extend_fields:
                    if getattr(group, field_name) is None:
                        setattr(group, field_name, [])
                    getattr(group, field_name).extend(value)
                    continue

                if "protocols" in field_name:
                    if isinstance(getattr(group, field_name), set):
                        value = _parse_protocol_set(value)
                    else:
                        value = _parse_protocol_list(value)

                setattr(group, field_name, value)


HANDLERS: Dict[str, Callable[..., None]] = {
    "fetch": commands.handle_fetch,
    "merge": commands.handle_merge,
    "retest": commands.handle_retest,
    "full": commands.handle_full,
    "daemon": commands.cmd_daemon,
    "tui": commands.handle_tui,
}


def main(argv: list[str] | None = None) -> None:
    """Main entry point for the `configstream` command."""
    print_public_source_warning()
    parser = build_parser()
    args = parser.parse_args(argv or sys.argv[1:])

    if args.command == "sources":
        sources_file = Path(args.sources_file)
        if args.sources_command == "list":
            services.list_sources(sources_file)
        elif args.sources_command == "add":
            services.add_new_source(sources_file, args.url)
        elif args.sources_command == "remove":
            services.remove_existing_source(sources_file, args.url)
        return

    try:
        cfg = load_config(Path(args.config))
    except (ValueError, FileNotFoundError):
        print("Config file not found. Using default settings.")
        cfg = Settings()

    _update_settings_from_args(cfg, args)

    if command_handler := HANDLERS.get(args.command):
        command_handler(args, cfg)


if __name__ == "__main__":
    main()
