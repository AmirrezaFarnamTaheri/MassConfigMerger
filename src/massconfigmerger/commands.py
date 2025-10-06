"""Command handler functions for the MassConfigMerger CLI.

This module contains the logic for executing the main application commands
(fetch, merge, retest, full) based on the parsed command-line arguments and
loaded application settings.
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from . import pipeline, vpn_merger, vpn_retester
from .config import Settings


def handle_fetch(args: argparse.Namespace, cfg: Settings) -> None:
    """
    Handler for the 'fetch' command.

    This function initiates the aggregation pipeline to collect VPN configurations
    from web sources and Telegram channels.
    """
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


def handle_merge(args: argparse.Namespace, cfg: Settings) -> None:
    """
    Handler for the 'merge' command.

    This function runs the VPN merger to test, sort, and merge configurations
    into a final subscription link.
    """
    asyncio.run(
        vpn_merger.run_merger(
            cfg,
            sources_file=Path(args.sources),
            resume_file=Path(args.resume_file) if args.resume_file else None,
        )
    )


def handle_retest(args: argparse.Namespace, cfg: Settings) -> None:
    """
    Handler for the 'retest' command.

    This function re-tests an existing subscription file to update the
    connectivity and latency information for each server.
    """
    asyncio.run(vpn_retester.run_retester(cfg, input_file=Path(args.input)))


def handle_full(args: argparse.Namespace, cfg: Settings) -> None:
    """
    Handler for the 'full' command.

    This function runs the full pipeline, which includes fetching configurations,
    and then merging and testing them.
    """
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