import pytest

flask = pytest.importorskip("flask")

from massconfigmerger import web
from massconfigmerger.config import Settings


def test_aggregate_endpoint(monkeypatch, tmp_path):
    def fake_run():
        return tmp_path, [tmp_path / "a.txt"]

    monkeypatch.setattr(web, "run_aggregator", fake_run)

    with web.app.test_client() as client:
        res = client.get("/aggregate")

    assert res.status_code == 200
    data = res.get_json()
    assert data == {
        "output_dir": str(tmp_path),
        "files": [str(tmp_path / "a.txt")],
    }


def test_merge_endpoint(monkeypatch):
    called = {}

    def fake_run():
        called["ok"] = True

    monkeypatch.setattr(web, "run_merger", fake_run)

    with web.app.test_client() as client:
        res = client.get("/merge")

    assert res.status_code == 200
    assert res.get_json() == {"status": "merge complete"}
    assert called.get("ok")


def test_report_endpoint_html(monkeypatch, tmp_path):
    html = tmp_path / "vpn_report.html"
    html.write_text("<h1>Report</h1>")

    monkeypatch.setattr(web, "load_cfg", lambda: Settings(output_dir=str(tmp_path)))

    with web.app.test_client() as client:
        res = client.get("/report")

    assert res.status_code == 200
    assert b"Report" in res.data
