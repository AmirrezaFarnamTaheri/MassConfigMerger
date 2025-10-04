"""Unified command-line interface for Mass Config Merger."""

import sys
import argparse
import asyncio
from pathlib import Path

from . import aggregator_tool, vpn_merger, vpn_retester
from .config import load_config, Settings
from .utils import print_public_source_warning
from .constants import SOURCES_FILE


def build_parser() -> argparse.ArgumentParser:
    """Build the main parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="massconfigmerger", description="Unified interface for Mass Config Merger"
    )
    parser.add_argument(
        "--config", default="config.yaml", help="Path to config.yaml"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- Parent Parsers for Shared Arguments ---
    network_parser = argparse.ArgumentParser(add_help=False)
    network_parser.add_argument(
        "--concurrent-limit", type=int, help="Maximum simultaneous HTTP requests"
    )
    network_parser.add_argument(
        "--request-timeout", type=int, help="HTTP request timeout in seconds"
    )

    filter_parser = argparse.ArgumentParser(add_help=False)
    filter_parser.add_argument("--protocols", help="Comma-separated protocols to keep")
    filter_parser.add_argument(
        "--include-pattern",
        action="append",
        help="Regular expression configs must match (can be repeated)",
    )
    filter_parser.add_argument(
        "--exclude-pattern",
        action="append",
        help="Regular expression to skip configs (can be repeated)",
    )

    output_parser = argparse.ArgumentParser(add_help=False)
    output_parser.add_argument("--output-dir", help="Override output directory from config")
    output_parser.add_argument(
        "--no-base64", action="store_true", help="skip vpn_subscription_base64.txt"
    )
    output_parser.add_argument(
        "--upload-gist",
        action="store_true",
        help="upload generated files to a GitHub Gist",
    )

    # --- Fetch Command Parser ---
    fetch_p = subparsers.add_parser(
        "fetch",
        help="Run the aggregation pipeline",
        parents=[network_parser, filter_parser, output_parser],
    )
    fetch_p.add_argument("--bot", action="store_true", help="run in telegram bot mode")
    fetch_p.add_argument(
        "--sources", default=str(SOURCES_FILE), help="path to sources.txt"
    )
    fetch_p.add_argument(
        "--channels", default="channels.txt", help="path to channels.txt"
    )
    fetch_p.add_argument(
        "--hours",
        type=int,
        default=24,
        help="how many hours of Telegram history to scan (default %(default)s)",
    )
    fetch_p.add_argument(
        "--failure-threshold",
        type=int,
        default=3,
        help="consecutive failures before pruning a source",
    )
    fetch_p.add_argument(
        "--no-prune", action="store_true", help="do not remove failing sources"
    )
    fetch_p.add_argument(
        "--no-singbox", action="store_true", help="skip vpn_singbox.json"
    )
    fetch_p.add_argument("--no-clash", action="store_true", help="skip clash.yaml")
    fetch_p.add_argument(
        "--shuffle-sources",
        action="store_true",
        help="process sources in random order",
    )
    fetch_p.add_argument(
        "--output-surge",
        metavar="FILE",
        type=str,
        default=None,
        help="write Surge formatted proxy list to FILE",
    )
    fetch_p.add_argument(
        "--output-qx",
        metavar="FILE",
        type=str,
        default=None,
        help="write Quantumult X formatted proxy list to FILE",
    )

    # --- Merge Command Parser ---
    merge_p = subparsers.add_parser(
        "merge",
        help="Run the VPN merger",
        parents=[network_parser, filter_parser, output_parser],
    )
    merge_p.add_argument(
        "--sources", default=str(SOURCES_FILE), help="Path to sources.txt"
    )
    merge_p.add_argument(
        "--resume", type=str, help="Resume from an existing subscription file"
    )
    merge_p.add_argument(
        "--no-sort", action="store_true", help="Disable sorting by latency"
    )
    merge_p.add_argument(
        "--top-n", type=int, default=0, help="Keep only the N fastest configs"
    )

    # --- Retest Command Parser ---
    retest_p = subparsers.add_parser(
        "retest", help="Retest an existing subscription", parents=[network_parser]
    )
    retest_p.add_argument(
        "input", help="Path to existing raw or base64 subscription file"
    )
    retest_p.add_argument(
        "--top-n", type=int, default=0, help="Keep only the N fastest configs"
    )
    retest_p.add_argument(
        "--no-sort", action="store_true", help="Skip sorting by latency"
    )
    retest_p.add_argument(
        "--connect-timeout",
        type=float,
        help="TCP connect timeout in seconds",
    )
    retest_p.add_argument(
        "--max-ping",
        type=int,
        help="Discard configs slower than this ping in ms (0 disables)",
    )
    retest_p.add_argument(
        "--include-protocols", type=str, help="Comma-separated protocols to include"
    )
    retest_p.add_argument(
        "--exclude-protocols",
        type=str,
        help="Comma-separated protocols to exclude",
    )
    retest_p.add_argument("--output-dir", type=str, help="Directory to save output files")
    retest_p.add_argument(
        "--no-base64", action="store_true", help="Do not save base64 file"
    )
    retest_p.add_argument("--no-csv", action="store_true", help="Do not save CSV report")

    # --- Full Command Parser ---
    full_p = subparsers.add_parser(
        "full",
        help="Aggregate, then merge and test configurations",
        parents=[network_parser, filter_parser, output_parser],
    )
    full_p.add_argument("--bot", action="store_true", help="run in telegram bot mode")
    full_p.add_argument(
        "--sources", default=str(SOURCES_FILE), help="path to sources.txt"
    )
    full_p.add_argument(
        "--channels", default="channels.txt", help="path to channels.txt"
    )
    full_p.add_argument(
        "--hours",
        type=int,
        default=24,
        help="how many hours of Telegram history to scan (default %(default)s)",
    )
    full_p.add_argument(
        "--failure-threshold",
        type=int,
        default=3,
        help="consecutive failures before pruning a source",
    )
    full_p.add_argument(
        "--no-prune", action="store_true", help="do not remove failing sources"
    )
    full_p.add_argument(
        "--no-singbox", action="store_true", help="skip vpn_singbox.json"
    )
    full_p.add_argument("--no-clash", action="store_true", help="skip clash.yaml")
    full_p.add_argument(
        "--shuffle-sources",
        action="store_true",
        help="process sources in random order",
    )
    full_p.add_argument(
        "--output-surge",
        metavar="FILE",
        type=str,
        default=None,
        help="write Surge formatted proxy list to FILE",
    )
    full_p.add_argument(
        "--output-qx",
        metavar="FILE",
        type=str,
        default=None,
        help="write Quantumult X formatted proxy list to FILE",
    )
    full_p.add_argument(
        "--no-sort", action="store_true", help="Disable sorting by latency"
    )
    full_p.add_argument(
        "--top-n", type=int, default=0, help="Keep only the N fastest configs"
    )

    return parser


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

    # Override config with CLI arguments
    for key, value in vars(args).items():
        if hasattr(cfg, key) and value is not None:
            setattr(cfg, key, value)

    if args.command == "fetch":
        asyncio.run(
            aggregator_tool.run_pipeline(
                cfg,
                protocols=args.protocols.split(",") if args.protocols else None,
                sources_file=Path(args.sources),
                channels_file=Path(args.channels),
                last_hours=args.hours,
                failure_threshold=args.failure_threshold,
                prune=not args.no_prune,
            )
        )
    elif args.command == "merge":
        asyncio.run(
            vpn_merger.run_merger(
                cfg,
                sources_file=Path(args.sources),
                protocols=args.protocols.split(",") if args.protocols else None,
                resume_file=Path(args.resume) if args.resume else None,
                sort=not args.no_sort,
                top_n=args.top_n,
            )
        )
    elif args.command == "retest":
        asyncio.run(
            vpn_retester.run_retester(
                cfg,
                input_file=Path(args.input),
                sort=not args.no_sort,
                top_n=args.top_n,
            )
        )
    elif args.command == "full":
        aggregator_output_dir, _ = asyncio.run(
            aggregator_tool.run_pipeline(
                cfg,
                protocols=args.protocols.split(",") if args.protocols else None,
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
                cfg,
                sources_file=Path(args.sources),
                protocols=args.protocols.split(",") if args.protocols else None,
                resume_file=resume_file,
                sort=not args.no_sort,
                top_n=args.top_n,
            )
        )


if __name__ == "__main__":
    main()