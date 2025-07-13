import asyncio

from massconfigmerger.vpn_merger import UltimateVPNMerger, ConfigResult, CONFIG


def test_maybe_save_batch_strict_cumulative(monkeypatch, tmp_path):
    monkeypatch.setattr(CONFIG, "save_every", 1)
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
