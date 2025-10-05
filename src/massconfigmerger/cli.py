"""Command-line interface for MassConfigMerger.

This module provides the main entry point for the `massconfigmerger` command-line
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

from . import cli_args, commands
try:
    from .config import Settings, load_config
except ImportError:
    from .config import Settings  # fallback
    def load_config(path=None):
        import logging
        logging.warning("Falling back to default Settings; load_config unavailable.")
        return Settings(config_file=path)
from .core.utils import print_public_source_warning
from .source_operations import (
    handle_add_source,
    handle_list_sources,
    handle_remove_source,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the main `argparse` parser with all subcommands and arguments."""
    parser = argparse.ArgumentParser(
        prog="massconfigmerger", description="A tool for collecting and merging VPN configurations."
    )
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Fetch command
    fetch_p = subparsers.add_parser("fetch", help="Run the aggregation pipeline")
    cli_args.add_fetch_arguments(fetch_p)

    # Merge command
    merge_p = subparsers.add_parser("merge", help="Run the VPN merger")
    cli_args.add_merge_arguments(merge_p)

    # Retest command
    retest_p = subparsers.add_parser("retest", help="Retest an existing subscription")
    cli_args.add_retest_arguments(retest_p)

    # Full command
    full_p = subparsers.add_parser(
        "full", help="Aggregate, then merge and test configurations"
    )
    cli_args.add_full_arguments(full_p)

    # Sources command
    cli_args.add_sources_parser(subparsers)

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

    # Direct mapping from arg name to (group, attribute)
    MAPPING = {
        "concurrent_limit": ("network", "concurrent_limit"),
        "request_timeout": ("network", "request_timeout"),
        "connect_timeout": ("network", "connect_timeout"),
        "max_ping_ms": ("filtering", "max_ping_ms"),
        "output_dir": ("output", "output_dir"),
        "surge_file": ("output", "surge_file"),
        "qx_file": ("output", "qx_file"),
        "write_base64": ("output", "write_base64"),
        "write_csv": ("output", "write_csv"),
        "upload_gist": ("output", "upload_gist"),
        "top_n": ("processing", "top_n"),
        "shuffle_sources": ("processing", "shuffle_sources"),
        "resume_file": ("processing", "resume_file"),
        "enable_sorting": ("processing", "enable_sorting"),
    }

    for arg_name, (group, attr) in MAPPING.items():
        if (value := arg_dict.get(arg_name)) is not None:
            setattr(getattr(cfg, group), attr, value)

    # Arguments requiring special parsing
    if "fetch_protocols" in arg_dict:
        cfg.filtering.fetch_protocols = _parse_protocol_list(
            arg_dict["fetch_protocols"]
        )
    if "merge_include_protocols" in arg_dict:
        cfg.filtering.merge_include_protocols = _parse_protocol_set(
            arg_dict["merge_include_protocols"]
        )
    if "merge_exclude_protocols" in arg_dict:
        cfg.filtering.merge_exclude_protocols = _parse_protocol_set(
            arg_dict["merge_exclude_protocols"]
        )

    # Arguments that are lists and need to be extended
    if "include_patterns" in arg_dict:
        cfg.filtering.include_patterns.extend(arg_dict["include_patterns"])
    if "exclude_patterns" in arg_dict:
        cfg.filtering.exclude_patterns.extend(arg_dict["exclude_patterns"])


HANDLERS: Dict[str, Callable[..., None]] = {
    "fetch": commands.handle_fetch,
    "merge": commands.handle_merge,
    "retest": commands.handle_retest,
    "full": commands.handle_full,
}

SOURCES_HANDLERS: Dict[str, Callable[[argparse.Namespace], None]] = {
    "list": handle_list_sources,
    "add": handle_add_source,
    "remove": handle_remove_source,
}


def main(argv: list[str] | None = None) -> None:
    """Main entry point for the `massconfigmerger` command."""
    print_public_source_warning()
    parser = build_parser()
    args = parser.parse_args(argv or sys.argv[1:])

    if args.command == "sources":
        if command_handler := SOURCES_HANDLERS.get(args.sources_command):
            command_handler(args)
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
