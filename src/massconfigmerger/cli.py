import sys
import argparse
from . import aggregator_tool
from . import vpn_merger


def main(argv: list[str] | None = None) -> None:
    """Entry point for the massconfigmerger command."""
    argv = list(sys.argv[1:] if argv is None else argv)

    parser = argparse.ArgumentParser(prog="massconfigmerger", description="Unified interface for Mass Config Merger")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_p = subparsers.add_parser("fetch", help="run the aggregation pipeline")
    fetch_p.add_argument("args", nargs=argparse.REMAINDER)

    merge_p = subparsers.add_parser("merge", help="run the VPN merger")
    merge_p.add_argument("args", nargs=argparse.REMAINDER)

    full_p = subparsers.add_parser("full", help="aggregate then merge")
    full_p.add_argument("args", nargs=argparse.REMAINDER)

    ns = parser.parse_args(argv)

    if ns.command == "fetch":
        sys.argv = ["aggregator-tool"] + ns.args
        aggregator_tool.main()
    elif ns.command == "merge":
        sys.argv = ["vpn-merger"] + ns.args
        vpn_merger.main()
    elif ns.command == "full":
        sys.argv = ["aggregator-tool"] + ns.args + ["--with-merger"]
        aggregator_tool.main()


if __name__ == "__main__":
    main()
