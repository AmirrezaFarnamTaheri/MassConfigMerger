from __future__ import annotations

from prometheus_client import generate_latest

from massconfigmerger import metrics


def test_metrics_definition():
    """Test that the Prometheus metrics are defined correctly."""
    assert metrics.SOURCES_FETCHED_TOTAL._name == "massconfigmerger_sources_fetched"
    assert metrics.SOURCES_FAILED_TOTAL._name == "massconfigmerger_sources_failed"
    assert metrics.CONFIGS_TESTED_TOTAL._name == "massconfigmerger_configs_tested"
    assert metrics.CONFIGS_REACHABLE_TOTAL._name == "massconfigmerger_configs_reachable"
    assert metrics.CONFIG_LATENCY_SECONDS._name == "massconfigmerger_config_latency_seconds"


def _get_metric_value(metric):
    """Get the current value of a Counter metric."""
    return metric.collect()[0].samples[0].value


def _get_histogram_bucket_value(histogram, bucket_le):
    """Get the current value of a Histogram bucket."""
    for sample in histogram.collect()[0].samples:
        if sample.name.endswith("_bucket") and sample.labels.get("le") == str(
            bucket_le
        ):
            return sample.value
    return 0


def test_metrics_generation():
    """Test the generation of the metrics report."""
    # Get current values before incrementing
    sources_fetched_before = _get_metric_value(metrics.SOURCES_FETCHED_TOTAL)
    sources_failed_before = _get_metric_value(metrics.SOURCES_FAILED_TOTAL)
    configs_tested_before = _get_metric_value(metrics.CONFIGS_TESTED_TOTAL)
    configs_reachable_before = _get_metric_value(metrics.CONFIGS_REACHABLE_TOTAL)
    latency_bucket_before = _get_histogram_bucket_value(
        metrics.CONFIG_LATENCY_SECONDS, 0.5
    )

    # Increment metrics
    metrics.SOURCES_FETCHED_TOTAL.inc(1)
    metrics.SOURCES_FAILED_TOTAL.inc(2)
    metrics.CONFIGS_TESTED_TOTAL.inc(3)
    metrics.CONFIGS_REACHABLE_TOTAL.inc(4)
    metrics.CONFIG_LATENCY_SECONDS.observe(0.5)

    # Generate the report
    text = generate_latest().decode("utf-8")

    # Assertions
    assert (
        f"massconfigmerger_sources_fetched_total {sources_fetched_before + 1.0}"
        in text
    )
    assert (
        f"massconfigmerger_sources_failed_total {sources_failed_before + 2.0}"
        in text
    )
    assert (
        f"massconfigmerger_configs_tested_total {configs_tested_before + 3.0}"
        in text
    )
    assert (
        f"massconfigmerger_configs_reachable_total {configs_reachable_before + 4.0}"
        in text
    )
    assert (
        f'massconfigmerger_config_latency_seconds_bucket{{le="0.5"}} {latency_bucket_before + 1.0}'
        in text
    )