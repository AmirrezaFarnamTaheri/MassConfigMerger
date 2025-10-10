"""Command handler functions for the ConfigStream CLI.

This module contains the logic for executing the main application commands
(fetch, merge, retest, full) by dispatching them to the appropriate services.
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from . import services
from .config import Settings
from .tui import display_results


def handle_fetch(args: argparse.Namespace, cfg: Settings) -> None:
    """Handler for the 'fetch' command."""
    asyncio.run(
        services.run_fetch_pipeline(
            cfg,
            sources_file=Path(args.sources),
            channels_file=Path(args.channels),
            last_hours=args.hours,
            failure_threshold=args.failure_threshold,
            prune=not args.no_prune,
        )
    )


def handle_merge(args: argparse.Namespace, cfg: Settings) -> None:
    """Handler for the 'merge' command."""
    asyncio.run(
        services.run_merge_pipeline(
            cfg,
            sources_file=Path(args.sources),
            resume_file=Path(args.resume_file) if args.resume_file else None,
        )
    )


def handle_retest(args: argparse.Namespace, cfg: Settings) -> None:
    """Handler for the 'retest' command."""
    asyncio.run(services.run_retest_pipeline(cfg, input_file=Path(args.input)))


def handle_full(args: argparse.Namespace, cfg: Settings) -> None:
    """Handler for the 'full' command."""
    asyncio.run(
        services.run_full_pipeline(
            cfg,
            sources_file=Path(args.sources),
            channels_file=Path(args.channels),
            last_hours=args.hours,
            failure_threshold=args.failure_threshold,
            prune=not args.no_prune,
        )
    )




def handle_tui(args: argparse.Namespace, cfg: Settings):
    """Handle the 'tui' command."""
    # This assumes the daemon has been run at least once to generate the results file.
    results_file = Path(cfg.output.output_dir) / "current_results.json"
    display_results(results_file)