import asyncio
import types

from massconfigmerger import aggregator_tool
from massconfigmerger.config import Settings


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


async def fake_fetch_text(session, url, timeout=10, *, retries=3, base_delay=1.0, **_):
    if "sub.example" in url:
        return "vmess://from_url"
    return None


def test_scrape_telegram_configs(monkeypatch, tmp_path):
    channels = tmp_path / "channels.txt"
    channels.write_text("chan1\n")
    cfg = Settings(
        telegram_api_id=1,
        telegram_api_hash="h",
        telegram_bot_token="t",
        allowed_user_ids=[1],
    )
    monkeypatch.setattr(aggregator_tool, "TelegramClient", DummyClient)
    monkeypatch.setattr(aggregator_tool, "Message", DummyMessage)
    monkeypatch.setattr(aggregator_tool, "fetch_text", fake_fetch_text)
    monkeypatch.setattr(
        aggregator_tool, "errors", types.SimpleNamespace(RPCError=Exception)
    )

    agg = aggregator_tool.Aggregator(cfg)
    result = asyncio.run(agg.scrape_telegram_configs(channels, 24))
    assert result == {"vmess://direct1", "vmess://from_url", "http://sub.example"}
