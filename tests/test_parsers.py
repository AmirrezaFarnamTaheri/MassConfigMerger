import pytest
from configstream.core import parse_config


def test_parse_vmess():
    config = "vmess://ewogICJ2IjogIjIiLAogICJwcyI6ICJqdS10dC5uYW1lIiwKICAiYWRkIjogImp1LXR0Lm5hbWUiLAogICJwb3J0IjogIjQ0MyIsCiAgImlkIjogIjAzZDAxMWYwLTM4ZTgtNGY5OS05YmY5LTUwMWQzYzdlMWY5MSIsCiAgImFpZCI6ICIwIiwKICAibmV0IjogIndzIiwKICAidHlwZSI6ICJub25lIiwKICAiaG9zdCI6ICJ3d3cuZ29vZ2xlLmNvbSIsCiAgInBhdGgiOiAiL2FsaXRhIiwKICAidGxzIjogInRscyIKfQ=="
    proxy = parse_config(config)
    assert proxy is not None
    assert proxy.protocol == "vmess"
    assert proxy.address == "ju-tt.name"


def test_parse_invalid():
    proxy = parse_config("invalid://config")
    assert proxy is None


def test_parse_empty():
    assert parse_config("") is None
    assert parse_config(None) is None