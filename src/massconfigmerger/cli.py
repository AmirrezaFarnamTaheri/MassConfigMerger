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
import asyncio
import sys
from pathlib import Path
from typing import Callable, Dict

from . import pipeline, vpn_merger, vpn_retester, source_operations
from .config import Settings
from .constants import SOURCES_FILE
from .core.config_loader import load_config
from .core.utils import print_public_source_warning


def _create_shared_parsers() -> Dict[str, argparse.ArgumentParser]:
    """Create parent parsers for arguments shared across multiple subcommands."""
    network_parser = argparse.ArgumentParser(add_help=False)
    network_parser.add_argument(
        "--concurrent-limit", type=int, help="Maximum simultaneous HTTP requests"
    )
    network_parser.add_argument(
        "--request-timeout", type=int, help="HTTP request timeout in seconds"
    )

    filter_parser = argparse.ArgumentParser(add_help=False)
    filter_parser.add_argument(
        "--include-pattern",
        dest="include_patterns",
        action="append",
        help="Regular expression for configs to match",
    )
    filter_parser.add_argument(
        "--exclude-pattern",
        dest="exclude_patterns",
        action="append",
        help="Regular expression for configs to skip",
    )

    output_parser = argparse.ArgumentParser(add_help=False)
    output_parser.add_argument(
        "--output-dir", help="Override output directory from config"
    )
    output_parser.add_argument(
        "--no-base64",
        dest="write_base64",
        action="store_false",
        help="Skip vpn_subscription_base64.txt",
    )
    output_parser.add_argument(
        "--upload-gist",
        action="store_true",
        help="Upload generated files to a GitHub Gist",
    )

    return {
        "network": network_parser,
        "filter": filter_parser,
        "output": output_parser,
    }


def _add_fetch_parser(
    subparsers: argparse._SubParsersAction, parents: Dict[str, argparse.ArgumentParser]
):
    """Add the 'fetch' command parser and its specific arguments."""
    fetch_p = subparsers.add_parser(
        "fetch", help="Run the aggregation pipeline", parents=list(parents.values())
    )
    _add_fetch_arguments(fetch_p)


def _add_fetch_arguments(parser: argparse.ArgumentParser):
    """Add arguments common to the 'fetch' and 'full' commands."""
    parser.add_argument("--bot", action="store_true", help="Run in Telegram bot mode")
    parser.add_argument(
        "--sources", default=str(SOURCES_FILE), help="Path to sources.txt"
    )
    parser.add_argument("--channels", default="channels.txt", help="Path to channels.txt")
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Hours of Telegram history to scan (default: %(default)s)",
    )
    parser.add_argument(
        "--failure-threshold",
        type=int,
        default=3,
        help="Consecutive failures before pruning a source",
    )
    parser.add_argument(
        "--no-prune", action="store_true", help="Do not remove failing sources"
    )
    parser.add_argument(
        "--shuffle-sources", action="store_true", help="Process sources in random order"
    )
    parser.add_argument(
        "--fetch-protocols",
        type=str,
        help="Comma-separated protocols to fetch from sources",
    )


def _add_merge_parser(
    subparsers: argparse._SubParsersAction, parents: Dict[str, argparse.ArgumentParser]
):
    """Add the 'merge' command parser and its specific arguments."""
    merge_p = subparsers.add_parser(
        "merge", help="Run the VPN merger", parents=list(parents.values())
    )
    merge_p.add_argument(
        "--sources", default=str(SOURCES_FILE), help="Path to sources.txt"
    )
    _add_merge_arguments(merge_p)


def _add_merge_arguments(parser: argparse.ArgumentParser):
    """Add arguments common to the 'merge' and 'full' commands."""
    parser.add_argument(
        "--resume",
        dest="resume_file",
        type=str,
        help="Resume from an existing subscription file",
    )
    parser.add_argument(
        "--no-sort",
        dest="enable_sorting",
        action="store_false",
        help="Disable sorting by latency",
    )
    parser.add_argument(
        "--top-n", type=int, default=0, help="Keep only the N fastest configs"
    )
    parser.add_argument(
        "--include-protocols",
        dest="merge_include_protocols",
        type=str,
        help="Comma-separated protocols to include in merged output",
    )
    parser.add_argument(
        "--exclude-protocols",
        dest="merge_exclude_protocols",
        type=str,
        help="Comma-separated protocols to exclude from merged output",
    )
    parser.add_argument(
        "--output-surge",
        dest="surge_file",
        metavar="FILE",
        type=str,
        help="Write Surge formatted proxy list to FILE",
    )
    parser.add_argument(
        "--output-qx",
        dest="qx_file",
        metavar="FILE",
        type=str,
        help="Write Quantumult X formatted proxy list to FILE",
    )


def _add_retest_parser(
    subparsers: argparse._SubParsersAction, parents: Dict[str, argparse.ArgumentParser]
):
    """Add the 'retest' command parser and its specific arguments."""
    retest_p = subparsers.add_parser(
        "retest",
        help="Retest an existing subscription",
        parents=[parents["network"]],
    )
    retest_p.add_argument(
        "input", help="Path to existing raw or base64 subscription file"
    )
    retest_p.add_argument(
        "--top-n", type=int, default=0, help="Keep only the N fastest configs"
    )
    retest_p.add_argument(
        "--no-sort", dest="enable_sorting", action="store_false", help="Skip sorting by latency"
    )
    retest_p.add_argument(
        "--connect-timeout", type=float, help="TCP connect timeout in seconds"
    )
    retest_p.add_argument(
        "--max-ping",
        dest="max_ping_ms",
        type=int,
        help="Discard configs slower than this ping in ms (0 disables)",
    )
    retest_p.add_argument(
        "--include-protocols",
        dest="merge_include_protocols",
        type=str,
        help="Comma-separated protocols to include",
    )
    retest_p.add_argument(
        "--exclude-protocols",
        dest="merge_exclude_protocols",
        type=str,
        help="Comma-separated protocols to exclude",
    )
    retest_p.add_argument("--output-dir", type=str, help="Directory to save output files")
    retest_p.add_argument(
        "--no-base64", dest="write_base64", action="store_false", help="Do not save base64 file"
    )
    retest_p.add_argument(
        "--no-csv", dest="write_csv", action="store_false", help="Do not save CSV report"
    )


def _add_full_parser(
    subparsers: argparse._SubParsersAction, parents: Dict[str, argparse.ArgumentParser]
):
    """Add the 'full' command parser, which combines 'fetch' and 'merge'."""
    full_p = subparsers.add_parser(
        "full",
        help="Aggregate, then merge and test configurations",
        parents=list(parents.values()),
    )
    _add_fetch_arguments(full_p)
    _add_merge_arguments(full_p)


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
        prog="massconfigmerger", description="Unified interface for Mass Config Merger"
    )
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    subparsers = parser.add_subparsers(dest="command", required=True)
    shared_parsers = _create_shared_parsers()
    _add_fetch_parser(subparsers, shared_parsers)
    _add_merge_parser(subparsers, shared_parsers)
    _add_retest_parser(subparsers, shared_parsers)
    _add_full_parser(subparsers, shared_parsers)
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
    """
    Update the `Settings` object with values from parsed command-line arguments.

    This function iterates through a mapping of CLI argument names to their
    corresponding locations in the `Settings` model, updating the configuration
    with any values provided by the user.

    Args:
        cfg: The `Settings` object to update.
        args: The `argparse.Namespace` object containing the parsed arguments.
    """
    arg_dict = vars(args)

    MAPPING = {
        "concurrent_limit": ("network", "concurrent_limit", None),
        "request_timeout": ("network", "request_timeout", None),
        "connect_timeout": ("network", "connect_timeout", None),
        "max_ping_ms": ("filtering", "max_ping_ms", None),
        "fetch_protocols": ("filtering", "fetch_protocols", _parse_protocol_list),
        "merge_include_protocols": (
            "filtering",
            "merge_include_protocols",
            _parse_protocol_set,
        ),
        "merge_exclude_protocols": (
            "filtering",
            "merge_exclude_protocols",
            _parse_protocol_set,
        ),
        "output_dir": ("output", "output_dir", None),
        "surge_file": ("output", "surge_file", None),
        "qx_file": ("output", "qx_file", None),
        "write_base64": ("output", "write_base64", None),
        "write_csv": ("output", "write_csv", None),
        "upload_gist": ("output", "upload_gist", None),
        "top_n": ("processing", "top_n", None),
        "shuffle_sources": ("processing", "shuffle_sources", None),
        "resume_file": ("processing", "resume_file", None),
        "enable_sorting": ("processing", "enable_sorting", None),
    }

    for arg_name, (group, attr, parser) in MAPPING.items():
        if (value := arg_dict.get(arg_name)) is not None:
            submodel = getattr(cfg, group)
            if parser:
                value = parser(value)
            setattr(submodel, attr, value)

    if (value := arg_dict.get("include_patterns")) is not None:
        cfg.filtering.include_patterns.extend(value)

    if (value := arg_dict.get("exclude_patterns")) is not None:
        cfg.filtering.exclude_patterns.extend(value)


def _handle_sources_list(args: argparse.Namespace):
    """Handler for the 'sources list' command."""
    sources = source_operations.list_sources(Path(args.sources_file))
    if sources:
        for source in sources:
            print(source)
    else:
        print("No sources found in the specified file.")


def _handle_sources_add(args: argparse.Namespace):
    """Handler for the 'sources add' command."""
    from urllib.parse import urlparse

    parsed_url = urlparse(args.url)
    if not (parsed_url.scheme in {"http", "https"} and parsed_url.netloc):
        print(f"Invalid URL format: {args.url}")
        return
    if source_operations.add_source(Path(args.sources_file), args.url):
        print(f"Source added: {args.url}")
    else:
        print(f"Source already exists: {args.url}")


def _handle_sources_remove(args: argparse.Namespace):
    """Handler for the 'sources remove' command."""
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(args.url)
    if not (parsed.scheme in {"http", "https"} and parsed.netloc):
        print(f"Invalid URL format: {args.url}")
        return
    # Normalize by removing fragments/query and ensuring lowercased scheme/host
    normalized = urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path or "",
            "",
            "",
            "",
        )
    )
    if source_operations.remove_source(Path(args.sources_file), normalized):
        print(f"Source removed: {normalized}")
    else:
        print(f"Source not found: {normalized}")


def _handle_fetch(args: argparse.Namespace, cfg: Settings):
    """Handler for the 'fetch' command."""
    asyncio.run(
        pipeline.run_aggregation_pipeline(
            cfg,
            sources_file=Path(args.sources),
            channels_file=Path(args.channels),
            last_hours=args.hours,
            failure_threshold=args.failure_threshold,
            prune=not args.no_prune,
        )
    )


def _handle_merge(args: argparse.Namespace, cfg: Settings):
    """Handler for the 'merge' command."""
    asyncio.run(
        vpn_merger.run_merger(
            cfg,
            sources_file=Path(args.sources),
            resume_file=Path(args.resume_file) if args.resume_file else None,
        )
    )


def _handle_retest(args: argparse.Namespace, cfg: Settings):
    """Handler for the 'retest' command."""
    asyncio.run(vpn_retester.run_retester(cfg, input_file=Path(args.input)))


def _handle_full(args: argparse.Namespace, cfg: Settings):
    """Handler for the 'full' command."""
    aggregator_output_dir, _ = asyncio.run(
        pipeline.run_aggregation_pipeline(
            cfg,
            sources_file=Path(args.sources),
            channels_file=Path(args.channels),
            last_hours=args.hours,
            failure_threshold=args.failure_threshold,
            prune=not args.no_prune,
        )
    )
    resume_file = aggregator_output_dir / "vpn_subscription_raw.txt"
    asyncio.run(
        vpn_merger.run_merger(
            cfg, sources_file=Path(args.sources), resume_file=resume_file
        )
    )


def main(argv: list[str] | None = None) -> None:
    """
    Main entry point for the `massconfigmerger` command.

    This function parses command-line arguments, loads the configuration,
    and calls the appropriate handler for the specified subcommand.

    Args:
        argv: A list of command-line arguments, or None to use `sys.argv`.
    """
    print_public_source_warning()
    if argv is None:
        argv = sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "sources":
        sources_handlers: Dict[str, Callable[[argparse.Namespace], None]] = {
            "list": _handle_sources_list,
            "add": _handle_sources_add,
            "remove": _handle_sources_remove,
        }
        command_handler = sources_handlers.get(args.sources_command)
        if command_handler:
            command_handler(args)
        return

    try:
        cfg = load_config(Path(args.config))
    except (ValueError, FileNotFoundError):
        print("Config file not found. Using default settings.")
        cfg = Settings()

    _update_settings_from_args(cfg, args)

    handlers: Dict[str, Callable[[argparse.Namespace, Settings], None]] = {
        "fetch": _handle_fetch,
        "merge": _handle_merge,
        "retest": _handle_retest,
        "full": _handle_full,
    }
    command_handler = handlers.get(args.command)
    if command_handler:
        command_handler(args, cfg)


if __name__ == "__main__":
    main()