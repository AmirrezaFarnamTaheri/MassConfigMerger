import asyncio
from pathlib import Path
from aiohttp import web
import pytest

from massconfigmerger.output_writer import upload_files_to_gist, write_upload_links


@pytest.mark.asyncio
async def test_upload_files_to_gist(aiohttp_client, tmp_path):
    f = tmp_path / "vpn_subscription_raw.txt"
    f.write_text("data", encoding="utf-8")

    async def handler(request):
        assert request.headers.get("Authorization") == "token secret"
        payload = await request.json()
        filename = next(iter(payload["files"]))
        return web.json_response({"files": {filename: {"raw_url": f"https://gist/{filename}"}}})

    app = web.Application()
    app.router.add_post("/gists", handler)
    client = await aiohttp_client(app)

    base = str(client.server.make_url(""))
    links = await upload_files_to_gist([f], "secret", base_url=base)
    assert links == {f.name: f"https://gist/{f.name}"}

    path = write_upload_links(links, tmp_path)
    assert path.read_text().strip() == f"{f.name}: https://gist/{f.name}"
