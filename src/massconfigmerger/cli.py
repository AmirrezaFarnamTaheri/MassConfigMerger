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
    filter_parser.add_argument("--protocols", help="Comma-separated protocols to keep")
    filter_parser.add_argument("--include-pattern", action="append", help="Regular expression for configs to match")
    filter_parser.add_argument("--exclude-pattern", action="append", help="Regular expression for configs to skip")

    output_parser = argparse.ArgumentParser(add_help=False)
    output_parser.add_argument("--output-dir", help="Override output directory from config")
    output_parser.add_argument("--no-base64", action="store_true", help="Skip vpn_subscription_base64.txt")
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
    parser.add_argument("--output-surge", metavar="FILE", type=str, help="Write Surge formatted proxy list to FILE")
    parser.add_argument("--output-qx", metavar="FILE", type=str, help="Write Quantumult X formatted proxy list to FILE")

def _add_merge_parser(subparsers: argparse._SubParsersAction, parents: Dict[str, argparse.ArgumentParser]):
    """Add the 'merge' command parser."""
    merge_p = subparsers.add_parser("merge", help="Run the VPN merger", parents=list(parents.values()))
    merge_p.add_argument("--sources", default=str(SOURCES_FILE), help="Path to sources.txt")
    _add_merge_arguments(merge_p)

def _add_merge_arguments(parser: argparse.ArgumentParser):
    """Add arguments common to merge and full commands."""
    parser.add_argument("--resume", type=str, help="Resume from an existing subscription file")
    parser.add_argument("--no-sort", action="store_true", help="Disable sorting by latency")
    parser.add_argument("--top-n", type=int, default=0, help="Keep only the N fastest configs")

def _add_retest_parser(subparsers: argparse._SubParsersAction, parents: Dict[str, argparse.ArgumentParser]):
    """Add the 'retest' command parser."""
    retest_p = subparsers.add_parser("retest", help="Retest an existing subscription", parents=[parents["network"]])
    retest_p.add_argument("input", help="Path to existing raw or base64 subscription file")
    retest_p.add_argument("--top-n", type=int, default=0, help="Keep only the N fastest configs")
    retest_p.add_argument("--no-sort", action="store_true", help="Skip sorting by latency")
    retest_p.add_argument("--connect-timeout", type=float, help="TCP connect timeout in seconds")
    retest_p.add_argument("--max-ping", type=int, help="Discard configs slower than this ping in ms (0 disables)")
    retest_p.add_argument("--include-protocols", type=str, help="Comma-separated protocols to include")
    retest_p.add_argument("--exclude-protocols", type=str, help="Comma-separated protocols to exclude")
    retest_p.add_argument("--output-dir", type=str, help="Directory to save output files")
    retest_p.add_argument("--no-base64", action="store_true", help="Do not save base64 file")
    retest_p.add_argument("--no-csv", action="store_true", help="Do not save CSV report")

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
    """Update settings from command-line arguments with explicit mapping."""
    mapping = {
        "concurrent_limit": ("network", "concurrent_limit"),
        "request_timeout": ("network", "request_timeout"),
        "connect_timeout": ("network", "connect_timeout"),
        "protocols": ("filtering", "protocols"),
        "include_pattern": ("filtering", "include_patterns"),
        "exclude_pattern": ("filtering", "exclude_patterns"),
        "max_ping": ("filtering", "max_ping_ms"),
        "include_protocols": ("filtering", "include_protocols"),
        "exclude_protocols": ("filtering", "exclude_protocols"),
        "output_dir": ("output", "output_dir"),
        "output_surge": ("output", "surge_file"),
        "output_qx": ("output", "qx_file"),
        "top_n": ("processing", "top_n"),
        "shuffle_sources": ("processing", "shuffle_sources"),
        "resume": ("processing", "resume_file"),
    }
    arg_dict = vars(args)

    for arg_key, val in arg_dict.items():
        if val is None:
            continue

        if arg_key == "no_base64":
            cfg.output.write_base64 = not val
            continue
        if arg_key == "no_csv":
            cfg.output.write_csv = not val
            continue
        if arg_key == "no_sort":
            cfg.processing.enable_sorting = not val
            continue

        if arg_key in ("include_pattern", "exclude_pattern"):
            field_name = mapping[arg_key][1]
            existing = getattr(cfg.filtering, field_name)
            setattr(cfg.filtering, field_name, existing + val)
            continue

        if arg_key in ("protocols", "include_protocols", "exclude_protocols"):
            if isinstance(val, str):
                val = {v.strip().upper() for v in val.split(",") if v.strip()}
            elif isinstance(val, list):
                val = {v.strip().upper() for v in val}

        target = mapping.get(arg_key)
        if target:
            submodel_name, field_name = target
            submodel = getattr(cfg, submodel_name)
            if hasattr(submodel, field_name):
                setattr(submodel, field_name, val)

def _handle_fetch(args: argparse.Namespace, cfg: Settings):
    asyncio.run(pipeline.run_aggregation_pipeline(cfg, protocols=args.protocols.split(",") if args.protocols else None, sources_file=Path(args.sources), channels_file=Path(args.channels), last_hours=args.hours, failure_threshold=args.failure_threshold, prune=not args.no_prune))

def _handle_merge(args: argparse.Namespace, cfg: Settings):
    asyncio.run(vpn_merger.run_merger(cfg, sources_file=Path(args.sources), protocols=args.protocols.split(",") if args.protocols else None, resume_file=Path(args.resume) if args.resume else None, sort=not args.no_sort, top_n=args.top_n))

def _handle_retest(args: argparse.Namespace, cfg: Settings):
    asyncio.run(vpn_retester.run_retester(cfg, input_file=Path(args.input), sort=not args.no_sort, top_n=args.top_n))

def _handle_full(args: argparse.Namespace, cfg: Settings):
    aggregator_output_dir, _ = asyncio.run(pipeline.run_aggregation_pipeline(cfg, protocols=args.protocols.split(",") if args.protocols else None, sources_file=Path(args.sources), channels_file=Path(args.channels), last_hours=args.hours, failure_threshold=args.failure_threshold, prune=not args.no_prune))
    resume_file = aggregator_output_dir / "vpn_subscription_raw.txt"
    asyncio.run(vpn_merger.run_merger(cfg, sources_file=Path(args.sources), protocols=args.protocols.split(",") if args.protocols else None, resume_file=resume_file, sort=not args.no_sort, top_n=args.top_n))

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