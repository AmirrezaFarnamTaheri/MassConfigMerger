import asyncio
import base64
from unittest.mock import AsyncMock, MagicMock

import pytest

from configstream.core import Proxy
from configstream.pipeline import (fetch_configs, process_proxies_in_batches,
                                   run_proxy_tests_in_batches)


@pytest.mark.asyncio
async def test_fetch_configs_plain_text():
    """Test fetching simple newline-delimited configs."""
    session = MagicMock()
    response = session.get.return_value.__aenter__.return_value
    response.text.return_value = "vless://proxy1\nvmess://proxy2"

    configs = await fetch_configs(session, "http://example.com/proxies.txt")

    assert configs == ["vless://proxy1", "vmess://proxy2"]


@pytest.mark.asyncio
async def test_fetch_configs_base64_encoded():
    """Test fetching a base64 encoded subscription."""
    session = MagicMock()
    plain_text_proxies = "vless://proxy1\nvmess://proxy2"
    b64_proxies = base64.b64encode(plain_text_proxies.encode()).decode()

    response = session.get.return_value.__aenter__.return_value
    response.text.return_value = b64_proxies

    configs = await fetch_configs(session, "http://example.com/sub.txt")

    assert configs == ["vless://proxy1", "vmess://proxy2"]


@pytest.mark.asyncio
async def test_fetch_configs_network_error():
    """Test that fetch_configs returns an empty list on network error."""
    session = MagicMock()
    session.get.side_effect = Exception("Network Timeout")

    configs = await fetch_configs(session, "http://example.com/failing.txt")

    assert configs == []


@pytest.mark.asyncio
async def test_proxy_batch_processing_logic():
    """Test the batch processing logic."""
    proxies = [
        Proxy(config=f"p{i}", protocol="http", address="a", port=i)
        for i in range(10)
    ]

    # Mock processor function that just returns the batch
    async def mock_processor(batch):
        await asyncio.sleep(0)  # yield control
        return batch

    processed_batches = []
    async for batch in process_proxies_in_batches(proxies,
                                                  mock_processor,
                                                  batch_size=3):
        processed_batches.append(batch)

    assert len(
        processed_batches) == 4  # 10 proxies in batches of 3 -> 3, 3, 3, 1
    assert len(processed_batches[0]) == 3
    assert len(processed_batches[1]) == 3
    assert len(processed_batches[2]) == 3
    assert len(processed_batches[3]) == 1
    assert processed_batches[0][0].config == "p0"
    assert processed_batches[3][0].config == "p9"


@pytest.mark.asyncio
async def test_test_proxies_batched_security_check():
    """Test that security checks are run for working proxies."""
    proxies = [
        Proxy(config="p1", protocol="http", address="a", port=1),
        Proxy(config="p2", protocol="http", address="b", port=2),
    ]

    # Mock tester to make one proxy work and one fail
    mock_tester = AsyncMock()
    mock_tester.test.side_effect = [
        Proxy(config="p1",
              protocol="http",
              address="a",
              port=1,
              is_working=True),
        Proxy(config="p2",
              protocol="http",
              address="b",
              port=2,
              is_working=False),
    ]

    # Mock detector to check if it's called
    mock_detector = AsyncMock()
    mock_detector.detect_malicious.return_value = {"is_malicious": False}

    results = await run_proxy_tests_in_batches(proxies, mock_tester,
                                               mock_detector)

    assert len(results) == 2
    # The detector should only be called for the working proxy
    mock_detector.detect_malicious.assert_called_once()
    assert results[0].is_working is True
    assert results[1].is_working is False


@pytest.mark.asyncio
async def test_test_proxies_batched_malicious_proxy():
    """Test that a malicious proxy is marked as not working."""
    proxies = [Proxy(config="p1", protocol="http", address="a", port=1)]

    mock_tester = AsyncMock()
    mock_tester.test.return_value = Proxy(config="p1",
                                          protocol="http",
                                          address="a",
                                          port=1,
                                          is_working=True)

    mock_detector = AsyncMock()
    mock_detector.detect_malicious.return_value = {
        "is_malicious": True,
        "severity": "HIGH",
        "tests": [MagicMock(passed=False)],
    }

    results = await run_proxy_tests_in_batches(proxies, mock_tester,
                                               mock_detector)

    assert results[0].is_working is False
    assert "Malicious: HIGH" in results[0].security_issues[0]


@pytest.mark.asyncio
async def test_fetch_configs_invalid_base64():
    """Test that fetch_configs handles invalid base64 content gracefully."""
    session = MagicMock()
    # This is a single line that is not valid base64
    invalid_b64 = "this is not base64"
    response = session.get.return_value.__aenter__.return_value
    response.text.return_value = invalid_b64

    # It should be treated as a plain text list of one item
    configs = await fetch_configs(session, "http://example.com/sub.txt")
    assert configs == ["this is not base64"]


@pytest.mark.asyncio
async def test_run_full_pipeline_rate_limited(tmp_path):
    """Test that a rate-limited source is correctly skipped."""
    sources = ["http://good.com", "http://ratelimited.com"]
    output_dir = tmp_path

    with patch("configstream.pipeline.fetch_configs") as mock_fetch, patch(
            "configstream.pipeline.run_proxy_tests_in_batches",
            return_value=[]), patch(
                "configstream.pipeline.geoip2.database.Reader"), patch(
                    "rich.progress.Progress") as mock_progress:

        mock_fetch.return_value = ["vless://proxy1"]

        # Mock the RateLimiter to only allow the first source
        mock_rate_limiter_instance = MagicMock()
        mock_rate_limiter_instance.is_allowed.side_effect = lambda url: url == "http://good.com"

        with patch("configstream.pipeline.RateLimiter",
                   return_value=mock_rate_limiter_instance):
            await run_full_pipeline(sources, str(output_dir), mock_progress)

            # fetch_configs should only be called for the non-rate-limited source
            mock_fetch.assert_called_once()
            assert mock_fetch.call_args[0][1] == "http://good.com"


@pytest.mark.asyncio
async def test_run_full_pipeline_geoip_load_error(tmp_path, capsys):
    """Test that a GeoIP database loading error is handled gracefully."""
    sources = ["http://source.com"]
    output_dir = tmp_path

    with patch("configstream.pipeline.fetch_configs",
               return_value=["vless://proxy1"]), patch(
                   "configstream.pipeline.run_proxy_tests_in_batches",
                   return_value=[]), patch(
                       "configstream.pipeline.Path.exists",
                       return_value=True), patch(
                           "configstream.pipeline.geoip2.database.Reader",
                           side_effect=Exception("DB Load Error")), patch(
                               "rich.progress.Progress") as mock_progress:

        await run_full_pipeline(sources, str(output_dir), mock_progress)

        captured = capsys.readouterr()
        assert "Could not load GeoIP database: DB Load Error" in captured.out


@pytest.mark.asyncio
async def test_run_full_pipeline_geoip_db_closed(tmp_path):
    """Test that the GeoIP database reader is properly closed after use."""
    sources = ["http://source.com"]
    output_dir = tmp_path

    mock_reader_instance = MagicMock()
    mock_reader_instance.city.return_value = MagicMock()

    with patch("configstream.pipeline.fetch_configs",
               return_value=["vless://proxy1"]), patch(
                   "configstream.pipeline.run_proxy_tests_in_batches",
                   return_value=[]), patch(
                       "configstream.pipeline.Path.exists",
                       return_value=True), patch(
                           "configstream.pipeline.geoip2.database.Reader",
                           return_value=mock_reader_instance), patch(
                               "rich.progress.Progress") as mock_progress:

        await run_full_pipeline(sources, str(output_dir), mock_progress)

        mock_reader_instance.close.assert_called_once()


@pytest.mark.asyncio
async def test_run_full_pipeline_filters(tmp_path):
    """Test that country and latency filters are correctly applied."""
    sources = ["http://source.com"]
    output_dir = tmp_path

    proxies_to_test = [
        Proxy(
            config="p1",
            protocol="http",
            address="a",
            port=1,
            is_working=True,
            latency=50,
            country_code="US",
        ),
        Proxy(
            config="p2",
            protocol="http",
            address="b",
            port=2,
            is_working=True,
            latency=150,
            country_code="DE",
        ),
        Proxy(
            config="p3",
            protocol="http",
            address="c",
            port=3,
            is_working=True,
            latency=250,
            country_code="US",
        ),
        Proxy(
            config="p4",
            protocol="http",
            address="d",
            port=4,
            is_working=False,
            latency=100,
            country_code="US",
        ),
    ]

    with patch("configstream.pipeline.fetch_configs", return_value=[]), patch(
            "configstream.pipeline.run_proxy_tests_in_batches",
            return_value=proxies_to_test
    ), patch("configstream.pipeline.geoip2.database.Reader"), patch(
            "rich.progress.Progress") as mock_progress, patch(
                "configstream.pipeline.Path.write_text") as mock_write_text:

        def find_proxies_json(calls):
            for call in calls:
                try:
                    data = json.loads(call.args[0])
                    if isinstance(data, list):
                        return data
                except (json.JSONDecodeError, TypeError):
                    continue
            return None

        # Test filtering by country
        mock_write_text.reset_mock()
        await run_full_pipeline(sources,
                                str(output_dir),
                                mock_progress,
                                country="US",
                                proxies=proxies_to_test.copy())
        written_data = find_proxies_json(mock_write_text.call_args_list)
        assert written_data is not None
        assert len(written_data) == 2
        assert written_data[0]["config"] == "p1"
        assert written_data[1]["config"] == "p3"

        # Test filtering by min_latency
        mock_write_text.reset_mock()
        await run_full_pipeline(sources,
                                str(output_dir),
                                mock_progress,
                                min_latency=100,
                                proxies=proxies_to_test.copy())
        written_data = find_proxies_json(mock_write_text.call_args_list)
        assert written_data is not None
        assert len(written_data) == 2
        assert written_data[0]["config"] == "p2"
        assert written_data[1]["config"] == "p3"

        # Test filtering by max_latency
        mock_write_text.reset_mock()
        await run_full_pipeline(sources,
                                str(output_dir),
                                mock_progress,
                                max_latency=200,
                                proxies=proxies_to_test.copy())
        written_data = find_proxies_json(mock_write_text.call_args_list)
        assert written_data is not None
        assert len(written_data) == 2
        assert written_data[0]["config"] == "p1"
        assert written_data[1]["config"] == "p2"
