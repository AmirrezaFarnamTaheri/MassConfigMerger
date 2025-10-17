#!/usr/bin/env python3
"""Legacy aggregator tool for backward compatibility"""

import sys
import click

@click.command()
@click.option('--with-merger', is_flag=True)
@click.option('--hours', type=int, default=24)
def main(with_merger, hours):
    """Legacy tool - redirects to main CLI"""
    from .cli import main as cli_main
    sys.argv = ['configstream', 'merge', '--sources', 'sources.txt', '--output', 'output/']
    return cli_main()

if __name__ == '__main__':
    main()