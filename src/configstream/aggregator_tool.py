#!/usr/bin/env python3
"""Legacy aggregator tool for backward compatibility"""

import subprocess
import sys

import click


@click.command()
@click.option("--with-merger", is_flag=True, help="Legacy option, not used.")
@click.option("--hours", type=int, default=24, help="Legacy option, not used.")
def main(with_merger, hours):
    """Legacy tool - redirects to main CLI"""
    print(
        "Legacy aggregator_tool is deprecated. Redirecting to `configstream merge`..."
    )

    args = [
        "configstream", "merge", "--sources", "sources.txt", "--output",
        "output/"
    ]
    try:
        subprocess.run(args, check=True)
    except FileNotFoundError:
        print(f"Error: The command 'configstream' was not found.",
              file=sys.stderr)
        print("Please ensure that the package is installed correctly.",
              file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"The command failed with exit code {e.returncode}",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
