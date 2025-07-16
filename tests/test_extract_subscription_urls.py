import pytest

from massconfigmerger.aggregator_tool import extract_subscription_urls


def test_extract_subscription_urls_basic():
    text = "Visit http://example.com and https://foo.bar." \
           " More: https://baz.qux) and http://spam.eggs], plus https://trim.com,."
    urls = extract_subscription_urls(text)
    assert "http://example.com" in urls
    assert "https://foo.bar" in urls
    assert "https://baz.qux" in urls
    assert "http://spam.eggs" in urls
    assert "https://trim.com" in urls
    assert all(not u.endswith((")", "]", ",", ".")) for u in urls)
