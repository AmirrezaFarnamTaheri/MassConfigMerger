"""Command handler functions for the ConfigStream CLI.

This module contains the logic for executing the main application commands
(fetch, merge, retest, full) by dispatching them to the appropriate services.
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import signal
import sys

from . import services
from .config import Settings
from .scheduler import TestScheduler
from .tui import display_results
from .web_dashboard import app


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


def cmd_daemon(args: argparse.Namespace, cfg: Settings):
    """Run the ConfigStream daemon with automated testing and web dashboard.

    This command starts:
    1. A scheduler that runs VPN tests every N hours
    2. A web server with the monitoring dashboard

    The daemon runs until interrupted (Ctrl+C or kill signal).
    """
    # Setup data directory
    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("ConfigStream Daemon Starting")
    print("=" * 70)
    print(f"Data directory: {data_dir.absolute()}")
    print(f"Test interval: {args.interval} hours")
    print(f"Web dashboard: http://{args.host}:{args.port}")
    print("=" * 70)

    # Initialize scheduler
    scheduler = TestScheduler(cfg, data_dir)

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print("\n" + "=" * 70)
        print("Shutting down gracefully...")
        print("=" * 70)
        scheduler.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start scheduler
    scheduler.start(interval_hours=args.interval)

    print("\n✓ Scheduler started")
    print(f"  Initial test: running now")
    print(f"  Next test: in {args.interval} hours")
    print(f"\nStarting web dashboard...")
    print(f"  URL: http://{args.host}:{args.port}")
    print(f"  Press Ctrl+C to stop\n")

    # Start Flask app (this blocks)
    try:
        app.run(
            host=args.host,
            port=args.port,
            debug=False,  # Don't use debug mode in daemon
            use_reloader=False  # Don't use reloader (conflicts with scheduler)
        )
    except Exception as e:
        print(f"Error starting web server: {e}")
        scheduler.stop()
        sys.exit(1)


def handle_tui(args: argparse.Namespace, cfg: Settings):
    """Handle the 'tui' command."""
    # This assumes the daemon has been run at least once to generate the results file.
    results_file = Path(cfg.output.output_dir) / "current_results.json"
    display_results(results_file)