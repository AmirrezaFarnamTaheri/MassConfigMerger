from configstream.config import Settings

def test_settings_load_defaults():
    """
    Test that the default settings are loaded correctly.
    """
    settings = Settings()
    assert settings.test_timeout == 5
    assert settings.test_max_workers == 10
    assert settings.output_dir == "output"
    assert settings.sources == []
