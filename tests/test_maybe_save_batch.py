import os
import sys
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from vpn_merger import UltimateVPNMerger, ConfigResult, CONFIG
import pytest


def test_maybe_save_batch_strict_cumulative(monkeypatch, tmp_path):
    monkeypatch.setattr(CONFIG, "batch_size", 1)
    monkeypatch.setattr(CONFIG, "strict_batch", True)
    monkeypatch.setattr(CONFIG, "cumulative_batches", True)
    monkeypatch.setattr(CONFIG, "enable_sorting", False)
    monkeypatch.setattr(CONFIG, "output_dir", str(tmp_path))

    merger = UltimateVPNMerger()

    async def dummy_generate(*_a, **_k):
        pass

    monkeypatch.setattr(UltimateVPNMerger, "_generate_comprehensive_outputs", dummy_generate)

    result = ConfigResult(
        config="vmess://a",
        protocol="VMess",
        host="host",
        port=80,
        ping_time=0.1,
        is_reachable=True,
        source_url="src",
    )
    merger.all_results.append(result)

    asyncio.run(asyncio.wait_for(merger._maybe_save_batch(), 0.5))

    assert merger.last_saved_count == len(merger.cumulative_unique)


@pytest.mark.asyncio
async def test_maybe_save_batch_concurrent(monkeypatch, tmp_path):
    monkeypatch.setattr(CONFIG, "batch_size", 1)
    monkeypatch.setattr(CONFIG, "strict_batch", False)
    monkeypatch.setattr(CONFIG, "cumulative_batches", True)
    monkeypatch.setattr(CONFIG, "enable_sorting", False)
    monkeypatch.setattr(CONFIG, "output_dir", str(tmp_path))

    merger = UltimateVPNMerger()

    async def dummy_generate(*_a, **_k):
        await asyncio.sleep(0)

    monkeypatch.setattr(UltimateVPNMerger, "_generate_comprehensive_outputs", dummy_generate)
    monkeypatch.setattr(UltimateVPNMerger, "_analyze_results", lambda self, r, s: {})

    def make_result(idx: int) -> ConfigResult:
        return ConfigResult(
            config=f"vmess://{idx}",
            protocol="VMess",
            host="h",
            port=80,
            ping_time=0.1,
            is_reachable=True,
            source_url=f"src{idx}",
        )

    async def worker(res: ConfigResult):
        merger.all_results.append(res)
        await merger._maybe_save_batch()

    tasks = [worker(make_result(i)) for i in range(5)]
    await asyncio.gather(*tasks)

    assert len(merger.cumulative_unique) == 5

