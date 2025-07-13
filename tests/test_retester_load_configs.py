import base64
import pytest
from massconfigmerger import vpn_retester


def test_load_base64(tmp_path):
    text = "vmess://a\nvless://b"
    data = base64.b64encode(text.encode()).decode()
    p = tmp_path / "subs.txt"
    p.write_text(data, encoding="utf-8")
    result = vpn_retester.load_configs(p)
    assert result == ["vmess://a", "vless://b"]


def test_load_base64_error(tmp_path):
    p = tmp_path / "bad.txt"
    p.write_text("a", encoding="utf-8")
    with pytest.raises(ValueError):
        vpn_retester.load_configs(p)


def test_decode_other_error(tmp_path, monkeypatch):
    p = tmp_path / "file.txt"
    p.write_text("data", encoding="utf-8")

    def boom(_):
        raise RuntimeError("boom")

    monkeypatch.setattr(vpn_retester.base64, "b64decode", boom)
    with pytest.raises(RuntimeError):
        vpn_retester.load_configs(p)


def test_load_unicode_decode_error(tmp_path):
    """Invalid UTF-8 bytes after base64 decoding should raise ValueError."""
    bad_bytes = b"\xff\xff"
    data = base64.b64encode(bad_bytes).decode()
    p = tmp_path / "bad_utf.txt"
    p.write_text(data, encoding="utf-8")
    with pytest.raises(ValueError):
        vpn_retester.load_configs(p)

