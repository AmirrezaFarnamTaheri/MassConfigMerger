"""Argument definitions for the ConfigStream CLI."""
from __future__ import annotations

import argparse

from .constants import (
    BASE64_SUBSCRIPTION_FILE_NAME,
    CHANNELS_FILE,
    SOURCES_FILE,
)


def add_shared_arguments(parser: argparse.ArgumentParser, *groups: str):
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
        group.add_argument(
            "--include-isps",
            dest="include_isps",
            type=str,
            help="Comma-separated list of ISPs to include",
        )
        group.add_argument(
            "--exclude-isps",
            dest="exclude_isps",
            type=str,
            help="Comma-separated list of ISPs to exclude",
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
            help=f"Skip {BASE64_SUBSCRIPTION_FILE_NAME}",
        )
        group.add_argument(
            "--upload-gist",
            action="store_true",
            help="Upload generated files to a GitHub Gist",
        )


def add_fetch_specific_arguments(
    parser: argparse.ArgumentParser, group_name: str = "fetch-specific arguments"
):
    """Add fetch-specific arguments to a parser under a named group."""
    group = parser.add_argument_group(group_name)
    group.add_argument("--bot", action="store_true",
                       help="Run in Telegram bot mode")
    group.add_argument(
        "--sources", default=str(SOURCES_FILE), help=f"Path to {SOURCES_FILE.name}"
    )
    group.add_argument(
        "--channels", default=str(CHANNELS_FILE), help=f"Path to {CHANNELS_FILE.name}"
    )
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


def add_merge_specific_arguments(
    parser: argparse.ArgumentParser,
    group_name: str = "merge-specific arguments",
    add_sources: bool = True,
):
    """Add merge-specific arguments to a parser under a named group."""
    group = parser.add_argument_group(group_name)
    if add_sources:
        group.add_argument(
            "--sources", default=str(SOURCES_FILE), help=f"Path to {SOURCES_FILE.name}"
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
        "--sort-by",
        dest="sort_by",
        type=str,
        choices=["latency", "reliability", "proximity"],
        help="Sort by latency, reliability, or proximity",
    )
    group.add_argument(
        "--proximity-latitude",
        dest="proximity_latitude",
        type=float,
        help="Your latitude for proximity sorting",
    )
    group.add_argument(
        "--proximity-longitude",
        dest="proximity_longitude",
        type=float,
        help="Your longitude for proximity sorting",
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


def add_fetch_arguments(parser: argparse.ArgumentParser):
    """Add arguments for the 'fetch' command."""
    add_shared_arguments(parser, "network", "filter", "output")
    add_fetch_specific_arguments(parser)


def add_merge_arguments(parser: argparse.ArgumentParser):
    """Add arguments for the 'merge' command."""
    add_shared_arguments(parser, "network", "filter", "output")
    add_merge_specific_arguments(parser)


def add_retest_arguments(parser: argparse.ArgumentParser):
    """Add arguments for the 'retest' command."""
    add_shared_arguments(parser, "network")
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
    group.add_argument("--output-dir", type=str,
                       help="Directory to save output files")
    group.add_argument(
        "--no-base64", dest="write_base64", action="store_false", help="Do not save base64 file"
    )
    group.add_argument(
        "--no-csv", dest="write_csv", action="store_false", help="Do not save CSV report"
    )


def add_full_arguments(parser: argparse.ArgumentParser):
    """Add arguments for the 'full' command."""
    add_shared_arguments(parser, "network", "filter", "output")
    add_fetch_specific_arguments(parser, group_name="fetch arguments")
    add_merge_specific_arguments(
        parser, group_name="merge arguments", add_sources=False)


def add_sources_parser(subparsers: argparse._SubParsersAction):
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
    add_p = sources_subparsers.add_parser(
        "add", help="Add a source to the list")
    add_p.add_argument("url", help="The URL of the source to add")
    remove_p = sources_subparsers.add_parser(
        "remove", help="Remove a source from the list"
    )
    remove_p.add_argument("url", help="The URL of the source to remove")


def add_daemon_arguments(parser: argparse.ArgumentParser):
    """Add arguments for the 'daemon' command."""
    parser.add_argument(
        "--interval-hours",
        type=int,
        default=2,
        help="The interval in hours for the automated testing cycle.",
    )
    parser.add_argument(
        "--web-port",
        type=int,
        default=8080,
        help="The port to run the web dashboard on.",
    )
    parser.add_argument(
        "--web-host",
        type=str,
        default="0.0.0.0",
        help="The host to run the web dashboard on.",
    )
