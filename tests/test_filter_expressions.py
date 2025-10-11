"""Test expression-based filtering."""
import pytest
from configstream.filtering.expressions import (
    FilterExpression,
    FilterParser,
    filter_nodes
)


def test_simple_comparison():
    """Test simple comparison expressions."""
    nodes = [
        {"ping_ms": 50, "country": "US"},
        {"ping_ms": 150, "country": "UK"},
        {"ping_ms": 250, "country": "US"}
    ]

    # Less than
    result = filter_nodes(nodes, "ping_ms < 100")
    assert len(result) == 1
    assert result[0]["ping_ms"] == 50
    print("✓ Less than operator works")

    # Greater than
    result = filter_nodes(nodes, "ping_ms > 100")
    assert len(result) == 2
    print("✓ Greater than operator works")

    # Equality
    result = filter_nodes(nodes, "country == 'US'")
    assert len(result) == 2
    print("✓ Equality operator works")


def test_compound_expressions():
    """Test AND/OR expressions."""
    nodes = [
        {"ping_ms": 50, "country": "US", "protocol": "vmess"},
        {"ping_ms": 150, "country": "US", "protocol": "shadowsocks"},
        {"ping_ms": 75, "country": "UK", "protocol": "vmess"}
    ]

    # AND
    result = filter_nodes(nodes, "ping_ms < 100 AND country == 'US'")
    assert len(result) == 1
    assert result[0]["ping_ms"] == 50
    print("✓ AND operator works")

    # OR
    result = filter_nodes(nodes, "country == 'US' OR protocol == 'vmess'")
    assert len(result) == 3
    print("✓ OR operator works")

    # Combined
    result = filter_nodes(
        nodes,
        "ping_ms < 100 AND (country == 'US' OR protocol == 'vmess')"
    )
    assert len(result) == 2
    print("✓ Combined expressions work")


def test_in_operator():
    """Test IN operator."""
    nodes = [
        {"protocol": "vmess"},
        {"protocol": "shadowsocks"},
        {"protocol": "trojan"}
    ]

    result = filter_nodes(nodes, "protocol IN ['vmess', 'shadowsocks']")
    assert len(result) == 2
    print("✓ IN operator works")


def test_not_operator():
    """Test NOT operator."""
    nodes = [
        {"is_blocked": True, "ping_ms": 50},
        {"is_blocked": False, "ping_ms": 75}
    ]

    result = filter_nodes(nodes, "NOT is_blocked")
    assert len(result) == 1
    assert result[0]["ping_ms"] == 75
    print("✓ NOT operator works")


if __name__ == "__main__":
    test_simple_comparison()
    test_compound_expressions()
    test_in_operator()
    test_not_operator()