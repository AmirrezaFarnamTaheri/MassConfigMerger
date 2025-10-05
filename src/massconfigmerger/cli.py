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

from . import commands
from .config import Settings, load_config
from .constants import SOURCES_FILE
from .core.utils import print_public_source_warning
from .source_operations import (
    handle_add_source,
    handle_list_sources,
    handle_remove_source,
)


def _add_shared_arguments(parser: argparse.ArgumentParser, *groups: str):
    """Add common argument groups to a parser."""
    if "network" in groups:
        group = parser.add_argument_group("network arguments")
        group.add_argument(
            "--concurrent-limit", type=int, help="Maximum simultaneous HTTP requests"
        )
        group.add_argument(
            "--request-timeout", type=int, help="HTTP request timeout in seconds"
        )
    if "filter" in groups:
        group = parser.add_argument_group("filter arguments")
        group.add_argument(
            "--include-pattern",
            dest="include_patterns",
            action="append",
            help="Regular expression for configs to match",
        )
        group.add_argument(
            "--exclude-pattern",
            dest="exclude_patterns",
            action="append",
            help="Regular expression for configs to skip",
        )
    if "output" in groups:
        group = parser.add_argument_group("output arguments")
        group.add_argument(
            "--output-dir", help="Override output directory from config"
        )
        group.add_argument(
            "--no-base64",
            dest="write_base64",
            action="store_false",
            help="Skip vpn_subscription_base64.txt",
        )
        group.add_argument(
            "--upload-gist",
            action="store_true",
            help="Upload generated files to a GitHub Gist",
        )


def _add_fetch_specific_arguments(
    parser: argparse.ArgumentParser, group_name: str = "fetch-specific arguments"
):
    """Add fetch-specific arguments to a parser under a named group."""
    group = parser.add_argument_group(group_name)
    group.add_argument("--bot", action="store_true", help="Run in Telegram bot mode")
    group.add_argument(
        "--sources", default=str(SOURCES_FILE), help="Path to sources.txt"
    )
    group.add_argument("--channels", default="channels.txt", help="Path to channels.txt")
    group.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Hours of Telegram history to scan (default: %(default)s)",
    )
    group.add_argument(
        "--failure-threshold",
        type=int,
        default=3,
        help="Consecutive failures before pruning a source",
    )
    group.add_argument(
        "--no-prune", action="store_true", help="Do not remove failing sources"
    )
    group.add_argument(
        "--shuffle-sources", action="store_true", help="Process sources in random order"
    )
    group.add_argument(
        "--fetch-protocols",
        type=str,
        help="Comma-separated protocols to fetch from sources",
    )


def _add_merge_specific_arguments(
    parser: argparse.ArgumentParser,
    group_name: str = "merge-specific arguments",
    add_sources: bool = True,
):
    """Add merge-specific arguments to a parser under a named group."""
    group = parser.add_argument_group(group_name)
    if add_sources:
        group.add_argument(
            "--sources", default=str(SOURCES_FILE), help="Path to sources.txt"
        )
    group.add_argument(
        "--resume",
        dest="resume_file",
        type=str,
        help="Resume from an existing subscription file",
    )
    group.add_argument(
        "--no-sort",
        dest="enable_sorting",
        action="store_false",
        help="Disable sorting by latency",
    )
    group.add_argument(
        "--top-n", type=int, default=0, help="Keep only the N fastest configs"
    )
    group.add_argument(
        "--include-protocols",
        dest="merge_include_protocols",
        type=str,
        help="Comma-separated protocols to include in merged output",
    )
    group.add_argument(
        "--exclude-protocols",
        dest="merge_exclude_protocols",
        type=str,
        help="Comma-separated protocols to exclude from merged output",
    )
    group.add_argument(
        "--output-surge",
        dest="surge_file",
        metavar="FILE",
        type=str,
        help="Write Surge formatted proxy list to FILE",
    )
    group.add_argument(
        "--output-qx",
        dest="qx_file",
        metavar="FILE",
        type=str,
        help="Write Quantumult X formatted proxy list to FILE",
    )


def _add_fetch_arguments(parser: argparse.ArgumentParser):
    """Add arguments for the 'fetch' command."""
    _add_shared_arguments(parser, "network", "filter", "output")
    _add_fetch_specific_arguments(parser)


def _add_merge_arguments(parser: argparse.ArgumentParser):
    """Add arguments for the 'merge' command."""
    _add_shared_arguments(parser, "network", "filter", "output")
    _add_merge_specific_arguments(parser)


def _add_retest_arguments(parser: argparse.ArgumentParser):
    """Add arguments for the 'retest' command."""
    _add_shared_arguments(parser, "network")
    group = parser.add_argument_group("retest-specific arguments")
    group.add_argument(
        "input", help="Path to existing raw or base64 subscription file"
    )
    group.add_argument(
        "--top-n", type=int, default=0, help="Keep only the N fastest configs"
    )
    group.add_argument(
        "--no-sort", dest="enable_sorting", action="store_false", help="Skip sorting by latency"
    )
    group.add_argument(
        "--connect-timeout", type=float, help="TCP connect timeout in seconds"
    )
    group.add_argument(
        "--max-ping",
        dest="max_ping_ms",
        type=int,
        help="Discard configs slower than this ping in ms (0 disables)",
    )
    group.add_argument(
        "--include-protocols",
        dest="merge_include_protocols",
        type=str,
        help="Comma-separated protocols to include",
    )
    group.add_argument(
        "--exclude-protocols",
        dest="merge_exclude_protocols",
        type=str,
        help="Comma-separated protocols to exclude",
    )
    group.add_argument("--output-dir", type=str, help="Directory to save output files")
    group.add_argument(
        "--no-base64", dest="write_base64", action="store_false", help="Do not save base64 file"
    )
    group.add_argument(
        "--no-csv", dest="write_csv", action="store_false", help="Do not save CSV report"
    )


def _add_full_arguments(parser: argparse.ArgumentParser):
    """Add arguments for the 'full' command."""
    _add_shared_arguments(parser, "network", "filter", "output")
    _add_fetch_specific_arguments(parser, group_name="fetch arguments")
    _add_merge_specific_arguments(parser, group_name="merge arguments", add_sources=False)


def _add_sources_parser(subparsers: argparse._SubParsersAction):
    """Add the 'sources' command parser for managing the sources list."""
    sources_p = subparsers.add_parser(
        "sources", help="Manage the list of subscription sources"
    )
    sources_p.add_argument(
        "--sources-file",
        default=str(SOURCES_FILE),
        help="Path to the sources file",
    )
    sources_subparsers = sources_p.add_subparsers(
        dest="sources_command", required=True
    )
    sources_subparsers.add_parser(
        "list", help="List all sources in the sources file"
    )
    add_p = sources_subparsers.add_parser("add", help="Add a source to the list")
    add_p.add_argument("url", help="The URL of the source to add")
    remove_p = sources_subparsers.add_parser(
        "remove", help="Remove a source from the list"
    )
    remove_p.add_argument("url", help="The URL of the source to remove")


def build_parser() -> argparse.ArgumentParser:
    """Build the main `argparse` parser with all subcommands and arguments."""
    parser = argparse.ArgumentParser(
        prog="massconfigmerger", description="A tool for collecting and merging VPN configurations."
    )
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Fetch command
    fetch_p = subparsers.add_parser("fetch", help="Run the aggregation pipeline")
    _add_fetch_arguments(fetch_p)

    # Merge command
    merge_p = subparsers.add_parser("merge", help="Run the VPN merger")
    _add_merge_arguments(merge_p)

    # Retest command
    retest_p = subparsers.add_parser("retest", help="Retest an existing subscription")
    _add_retest_arguments(retest_p)

    # Full command
    full_p = subparsers.add_parser(
        "full", help="Aggregate, then merge and test configurations"
    )
    _add_full_arguments(full_p)

    # Sources command
    _add_sources_parser(subparsers)

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
