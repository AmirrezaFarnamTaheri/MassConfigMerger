def test_categorize_protocol_case_insensitive():
    from massconfigmerger.result_processor import EnhancedConfigProcessor

    proc = EnhancedConfigProcessor()
    assert proc.categorize_protocol("VMESS://foo") == "VMess"
    assert proc.categorize_protocol("Ss://foo") == "Shadowsocks"
    assert proc.categorize_protocol("VLESS://foo") == "VLESS"
    assert proc.categorize_protocol("WIREGUARD://foo") == "WireGuard"
