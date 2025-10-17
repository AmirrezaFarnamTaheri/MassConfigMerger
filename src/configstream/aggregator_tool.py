#!/usr/bin/env python3
"""Legacy aggregator tool for backward compatibility"""

import click

@click.command()
@click.option('--with-merger', is_flag=True, help="Legacy option, not used.")
@click.option('--hours', type=int, default=24, help="Legacy option, not used.")
def main(with_merger, hours):
    """Legacy tool - redirects to main CLI"""
    from .cli import main as cli_main
    # It's better to call the function with arguments than to manipulate sys.argv
    # The arguments are hardcoded as per the original logic.
    args = ['merge', '--sources', 'sources.txt', '--output', 'output/']
    return cli_main(args)

if __name__ == '__main__':
    main()
