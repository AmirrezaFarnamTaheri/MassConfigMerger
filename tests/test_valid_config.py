import base64
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from aggregator_tool import is_valid_config

def test_vmess_with_fragment_accepted():
    data = {"v": "2", "ps": "test"}
    b64 = base64.b64encode(json.dumps(data).encode()).decode().strip("=")
    link = f"vmess://{b64}#note"
    assert is_valid_config(link)
