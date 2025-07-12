# flake8: noqa
import asyncio
import types
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import aggregator_tool


class DummyMessage:
    def __init__(self, msg):
        self.message = msg


class DummyClient:
    def __init__(self, *a, **k):
        pass

    async def start(self):
        return self

    async def iter_messages(self, channel, offset_date=None):
        messages = [
            DummyMessage("vmess://direct1"),
            DummyMessage("http://sub.example"),
        ]
        for m in messages:
            yield m

    async def disconnect(self):
        pass

    async def connect(self):
        pass


async def fake_fetch_text(session, url, timeout=10):
    if "sub.example" in url:
        return "vmess://from_url"
    return None


def test_scrape_telegram_configs(monkeypatch, tmp_path):
    channels = tmp_path / "channels.txt"
    channels.write_text("chan1\n")
    cfg = aggregator_tool.Config(
        telegram_api_id=1,
        telegram_api_hash="h",
        telegram_bot_token="t",
        allowed_user_ids=[1],
    )
    monkeypatch.setattr(aggregator_tool, "TelegramClient", DummyClient)
    monkeypatch.setattr(aggregator_tool, "Message", DummyMessage)
    monkeypatch.setattr(aggregator_tool, "fetch_text", fake_fetch_text)
    monkeypatch.setattr(aggregator_tool, "errors", types.SimpleNamespace(RPCError=Exception))

    result = asyncio.run(aggregator_tool.scrape_telegram_configs(channels, 24, cfg))
    assert result == {"vmess://direct1", "vmess://from_url", "http://sub.example"}
