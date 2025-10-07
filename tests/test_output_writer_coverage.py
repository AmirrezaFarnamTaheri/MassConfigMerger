import pytest
from pathlib import Path
from unittest.mock import patch

from configstream.config import Settings
from configstream.output_writer import write_all_outputs, write_clash_proxies
from configstream.core.config_processor import ConfigResult

@pytest.fixture
def mock_results() -> list[ConfigResult]:
    """Fixture for mock ConfigResult objects."""
    return [
        ConfigResult(
            config="vless://test1",
            protocol="VLESS",
            host="example.com",
            port=443,
            ping_time=0.1,
            is_reachable=True,
            source_url="http://source.com/1",
            country="US",
        )
    ]

@pytest.fixture
def mock_settings_fs(fs) -> Settings:
    """Fixture for a default Settings object with a fake output directory for pyfakefs tests."""
    settings = Settings()
    settings.output.output_dir = Path("fake_output")
    return settings

def test_write_all_outputs_html_enabled(mock_settings_fs: Settings, mock_results: list[ConfigResult]):
    """Test that the HTML report is generated when enabled."""
    mock_settings_fs.output.write_html = True
    with patch("configstream.output_writer.generate_html_report") as mock_gen_html:
        write_all_outputs(mock_results, mock_settings_fs, {}, 0.0)
        mock_gen_html.assert_called_once()

def test_write_all_outputs_surge_enabled(mock_settings_fs: Settings, mock_results: list[ConfigResult]):
    """Test that the Surge file is generated when enabled."""
    mock_settings_fs.output.surge_file = Path("surge.conf")
    surge_content = "[Proxy]\nMyProxy = http, example.com, 80"

    with patch("configstream.output_writer.generate_surge_conf", return_value=surge_content), \
         patch("configstream.output_writer.config_to_clash_proxy", return_value={"name": "MyProxy"}):
        written_files = write_all_outputs(mock_results, mock_settings_fs, {}, 0.0)

        surge_file = mock_settings_fs.output.output_dir / "surge.conf"
        assert surge_file in written_files
        assert surge_file.read_text() == surge_content

def test_write_all_outputs_qx_enabled(mock_settings_fs: Settings, mock_results: list[ConfigResult]):
    """Test that the Quantumult X file is generated when enabled."""
    mock_settings_fs.output.qx_file = Path("qx.conf")
    qx_content = "vmess=example.com:443"

    with patch("configstream.output_writer.generate_qx_conf", return_value=qx_content), \
         patch("configstream.output_writer.config_to_clash_proxy", return_value={"name": "MyProxy"}):
        written_files = write_all_outputs(mock_results, mock_settings_fs, {}, 0.0)

        qx_file = mock_settings_fs.output.output_dir / "qx.conf"
        assert qx_file in written_files
        assert qx_file.read_text() == qx_content

@patch("configstream.output_writer.config_to_clash_proxy", return_value=None)
def test_write_clash_proxies_no_valid_proxies(mock_clash_proxy, tmp_path: Path, mock_results: list[ConfigResult]):
    """Test write_clash_proxies when no configs can be converted."""
    output_file = write_clash_proxies(mock_results, tmp_path)
    assert 'proxies: []' in output_file.read_text()

def test_write_all_outputs_advanced_formats_no_proxies(mock_settings_fs: Settings):
    """Test that advanced format files are not written if no proxies are generated."""
    mock_settings_fs.output.surge_file = Path("surge.conf")
    mock_settings_fs.output.qx_file = Path("qx.conf")

    # Pass empty results, so no proxies are generated
    written_files = write_all_outputs([], mock_settings_fs, {}, 0.0)

    surge_file = mock_settings_fs.output.output_dir / "surge.conf"
    qx_file = mock_settings_fs.output.output_dir / "qx.conf"

    assert surge_file not in written_files
    assert not surge_file.exists()
    assert qx_file not in written_files
    assert not qx_file.exists()