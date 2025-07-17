import pytest
from massconfigmerger import cli


def no_call(*_a, **_k):
    raise AssertionError("unexpected call")


def test_cli_fetch_invokes_aggregator(monkeypatch):
    called = {}

    monkeypatch.setattr(cli, "print_public_source_warning", lambda: None)
    monkeypatch.setattr(cli.aggregator_tool, "main", lambda ns: called.setdefault("args", ns))
    monkeypatch.setattr(cli.vpn_merger, "main", no_call)
    monkeypatch.setattr(cli.vpn_retester, "main", no_call)

    cli.main(["fetch"])

    assert called["args"].command == "fetch"


def test_cli_merge_invokes_vpn_merger(monkeypatch):
    called = {}

    monkeypatch.setattr(cli, "print_public_source_warning", lambda: None)
    monkeypatch.setattr(cli.aggregator_tool, "main", no_call)
    monkeypatch.setattr(cli.vpn_retester, "main", no_call)
    monkeypatch.setattr(cli.vpn_merger, "main", lambda ns: called.setdefault("args", ns))

    cli.main(["merge"])

    assert called["args"].command == "merge"


def test_cli_retest_invokes_retester(monkeypatch):
    called = {}

    monkeypatch.setattr(cli, "print_public_source_warning", lambda: None)
    monkeypatch.setattr(cli.aggregator_tool, "main", no_call)
    monkeypatch.setattr(cli.vpn_merger, "main", no_call)
    monkeypatch.setattr(cli.vpn_retester, "main", lambda ns: called.setdefault("args", ns))

    cli.main(["retest", "dummy"])

    assert called["args"].command == "retest"


def test_cli_full_invokes_aggregator_with_merger(monkeypatch):
    called = {}

    monkeypatch.setattr(cli, "print_public_source_warning", lambda: None)
    monkeypatch.setattr(cli.aggregator_tool, "main", lambda ns: called.setdefault("args", ns))
    monkeypatch.setattr(cli.vpn_merger, "main", no_call)
    monkeypatch.setattr(cli.vpn_retester, "main", no_call)

    cli.main(["full"])

    args = called["args"]
    assert args.command == "full"
    assert getattr(args, "with_merger", False) is True
