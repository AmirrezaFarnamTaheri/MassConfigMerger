"""Unified command-line interface for Mass Config Merger."""

import sys
import argparse
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Callable

from . import pipeline, vpn_merger, vpn_retester
from .config import load_config, Settings
from .core.utils import print_public_source_warning
from .constants import SOURCES_FILE


def _create_shared_parsers() -> Dict[str, argparse.ArgumentParser]:
    """Create parent parsers for shared arguments."""
    network_parser = argparse.ArgumentParser(add_help=False)
    network_parser.add_argument("--concurrent-limit", type=int, help="Maximum simultaneous HTTP requests")
    network_parser.add_argument("--request-timeout", type=int, help="HTTP request timeout in seconds")

    filter_parser = argparse.ArgumentParser(add_help=False)
    filter_parser.add_argument(
        "--include-pattern", dest="include_patterns", action="append", help="Regular expression for configs to match"
    )
    filter_parser.add_argument(
        "--exclude-pattern", dest="exclude_patterns", action="append", help="Regular expression for configs to skip"
    )

    output_parser = argparse.ArgumentParser(add_help=False)
    output_parser.add_argument("--output-dir", help="Override output directory from config")
    output_parser.add_argument(
        "--no-base64", dest="write_base64", action="store_false", help="Skip vpn_subscription_base64.txt"
    )
    output_parser.add_argument("--upload-gist", action="store_true", help="Upload generated files to a GitHub Gist")

    return {"network": network_parser, "filter": filter_parser, "output": output_parser}


def _add_fetch_parser(subparsers: argparse._SubParsersAction, parents: Dict[str, argparse.ArgumentParser]):
    """Add the 'fetch' command parser."""
    fetch_p = subparsers.add_parser("fetch", help="Run the aggregation pipeline", parents=list(parents.values()))
    _add_fetch_arguments(fetch_p)


def _add_fetch_arguments(parser: argparse.ArgumentParser):
    """Add arguments common to fetch and full commands."""
    parser.add_argument("--bot", action="store_true", help="Run in Telegram bot mode")
    parser.add_argument("--sources", default=str(SOURCES_FILE), help="Path to sources.txt")
    parser.add_argument("--channels", default="channels.txt", help="Path to channels.txt")
    parser.add_argument("--hours", type=int, default=24, help="Hours of Telegram history to scan (default: %(default)s)")
    parser.add_argument("--failure-threshold", type=int, default=3, help="Consecutive failures before pruning a source")
    parser.add_argument("--no-prune", action="store_true", help="Do not remove failing sources")
    parser.add_argument("--shuffle-sources", action="store_true", help="Process sources in random order")
    parser.add_argument("--fetch-protocols", type=str, help="Comma-separated protocols to fetch from sources")


def _add_merge_parser(subparsers: argparse._SubParsersAction, parents: Dict[str, argparse.ArgumentParser]):
    """Add the 'merge' command parser."""
    merge_p = subparsers.add_parser("merge", help="Run the VPN merger", parents=list(parents.values()))
    merge_p.add_argument("--sources", default=str(SOURCES_FILE), help="Path to sources.txt")
    _add_merge_arguments(merge_p)


def _add_merge_arguments(parser: argparse.ArgumentParser):
    """Add arguments common to merge and full commands."""
    parser.add_argument("--resume", dest="resume_file", type=str, help="Resume from an existing subscription file")
    parser.add_argument("--no-sort", dest="enable_sorting", action="store_false", help="Disable sorting by latency")
    parser.add_argument("--top-n", type=int, default=0, help="Keep only the N fastest configs")
    parser.add_argument("--include-protocols", dest="merge_include_protocols", type=str, help="Comma-separated protocols to include in merged output")
    parser.add_argument("--exclude-protocols", dest="merge_exclude_protocols", type=str, help="Comma-separated protocols to exclude from merged output")
    parser.add_argument("--output-surge", dest="surge_file", metavar="FILE", type=str, help="Write Surge formatted proxy list to FILE")
    parser.add_argument("--output-qx", dest="qx_file", metavar="FILE", type=str, help="Write Quantumult X formatted proxy list to FILE")


def _add_retest_parser(subparsers: argparse._SubParsersAction, parents: Dict[str, argparse.ArgumentParser]):
    """Add the 'retest' command parser."""
    retest_p = subparsers.add_parser("retest", help="Retest an existing subscription", parents=[parents["network"]])
    retest_p.add_argument("input", help="Path to existing raw or base64 subscription file")
    retest_p.add_argument("--top-n", type=int, default=0, help="Keep only the N fastest configs")
    retest_p.add_argument("--no-sort", dest="enable_sorting", action="store_false", help="Skip sorting by latency")
    retest_p.add_argument("--connect-timeout", type=float, help="TCP connect timeout in seconds")
    retest_p.add_argument("--max-ping", dest="max_ping_ms", type=int, help="Discard configs slower than this ping in ms (0 disables)")
    retest_p.add_argument("--include-protocols", dest="merge_include_protocols", type=str, help="Comma-separated protocols to include")
    retest_p.add_argument("--exclude-protocols", dest="merge_exclude_protocols", type=str, help="Comma-separated protocols to exclude")
    retest_p.add_argument("--output-dir", type=str, help="Directory to save output files")
    retest_p.add_argument("--no-base64", dest="write_base64", action="store_false", help="Do not save base64 file")
    retest_p.add_argument("--no-csv", dest="write_csv", action="store_false", help="Do not save CSV report")


def _add_full_parser(subparsers: argparse._SubParsersAction, parents: Dict[str, argparse.ArgumentParser]):
    """Add the 'full' command parser."""
    full_p = subparsers.add_parser("full", help="Aggregate, then merge and test configurations", parents=list(parents.values()))
    _add_fetch_arguments(full_p)
    _add_merge_arguments(full_p)


def build_parser() -> argparse.ArgumentParser:
    """Build the main parser with subcommands."""
    parser = argparse.ArgumentParser(prog="massconfigmerger", description="Unified interface for Mass Config Merger")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    subparsers = parser.add_subparsers(dest="command", required=True)
    shared_parsers = _create_shared_parsers()
    _add_fetch_parser(subparsers, shared_parsers)
    _add_merge_parser(subparsers, shared_parsers)
    _add_retest_parser(subparsers, shared_parsers)
    _add_full_parser(subparsers, shared_parsers)
    return parser


def _update_settings_from_args(cfg: Settings, args: argparse.Namespace):
    """Update settings from command-line arguments."""
    arg_to_submodel = {
        "concurrent_limit": "network", "request_timeout": "network", "connect_timeout": "network",
        "fetch_protocols": "filtering", "include_patterns": "filtering", "exclude_patterns": "filtering",
        "merge_include_protocols": "filtering", "merge_exclude_protocols": "filtering", "max_ping_ms": "filtering",
        "output_dir": "output", "surge_file": "output", "qx_file": "output",
        "write_base64": "output", "write_csv": "output", "upload_gist": "output",
        "top_n": "processing", "shuffle_sources": "processing", "resume_file": "processing",
        "enable_sorting": "processing",
    }
    arg_dict = vars(args)

    for arg_key, val in arg_dict.items():
        if val is None or arg_key not in arg_to_submodel:
            continue

        if arg_key in ("include_patterns", "exclude_patterns"):
            submodel = getattr(cfg, arg_to_submodel[arg_key])
            existing = getattr(submodel, arg_key)
            setattr(submodel, arg_key, existing + (val or []))
            continue

        if arg_key in ("fetch_protocols", "merge_include_protocols", "merge_exclude_protocols"):
            if isinstance(val, str):
                val = {v.strip().upper() for v in val.split(",") if v.strip()}
            elif isinstance(val, list):
                val = {v.strip().upper() for v in val}

        submodel_name = arg_to_submodel[arg_key]
        submodel = getattr(cfg, submodel_name)
        if hasattr(submodel, arg_key):
            setattr(submodel, arg_key, val)


def _handle_fetch(args: argparse.Namespace, cfg: Settings):
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
    asyncio.run(
        vpn_merger.run_merger(
            cfg,
            sources_file=Path(args.sources),
            resume_file=Path(args.resume_file) if args.resume_file else None,
        )
    )


def _handle_retest(args: argparse.Namespace, cfg: Settings):
    asyncio.run(vpn_retester.run_retester(cfg, input_file=Path(args.input)))


def _handle_full(args: argparse.Namespace, cfg: Settings):
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
    asyncio.run(vpn_merger.run_merger(cfg, sources_file=Path(args.sources), resume_file=resume_file))


def main(argv: list[str] | None = None) -> None:
    """Entry point for the massconfigmerger command."""
    print_public_source_warning()
    if argv is None:
        argv = sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)
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