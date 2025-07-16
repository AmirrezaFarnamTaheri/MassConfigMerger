import sys
import argparse
from .utils import print_public_source_warning
from . import aggregator_tool
from . import vpn_merger
from . import vpn_retester


def main(argv: list[str] | None = None) -> None:
    """Entry point for the massconfigmerger command."""
    print_public_source_warning()
    argv = list(sys.argv[1:] if argv is None else argv)

    parser = argparse.ArgumentParser(prog="massconfigmerger", description="Unified interface for Mass Config Merger")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_p = subparsers.add_parser("fetch", help="run the aggregation pipeline")
    aggregator_tool.build_parser(fetch_p)

    merge_p = subparsers.add_parser("merge", help="run the VPN merger")
    vpn_merger.build_parser(merge_p)

    retest_p = subparsers.add_parser("retest", help="retest an existing subscription")
    vpn_retester.build_parser(retest_p)

    full_p = subparsers.add_parser("full", help="aggregate then merge")
    aggregator_tool.build_parser(full_p)
    full_p.set_defaults(with_merger=True)

    ns = parser.parse_args(argv)

    if ns.command == "fetch":
        aggregator_tool.main(ns)
    elif ns.command == "merge":
        vpn_merger.main(ns)
    elif ns.command == "retest":
        vpn_retester.main(ns)
    elif ns.command == "full":
        aggregator_tool.main(ns)


if __name__ == "__main__":
    main()
