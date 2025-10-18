import asyncio
import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from configstream.core import Proxy
from configstream.pipeline import run_full_pipeline


@pytest.mark.asyncio
async def test_pipeline_no_sources():
    result = await run_full_pipeline(sources=[], output_dir="/tmp/test")
    assert result["success"] is False
    assert result["stats"]["fetched"] == 0


@pytest.mark.asyncio
async def test_pipeline_unparseable_config(tmp_path):
    with patch("configstream.pipeline._fetch_source",
               return_value=(["invalid config"], 1)):
        result = await run_full_pipeline(sources=["http://returns-garbage.com"],
                                         output_dir=tmp_path)
        assert result["success"] is False
        assert result["stats"]["fetched"] == 1
        assert result["stats"]["tested"] == 0