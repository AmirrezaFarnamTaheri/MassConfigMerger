from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Proxy:
    """Represents a proxy with its configuration and test results."""
    config: str
    protocol: str
    address: str
    port: int
    uuid: str = ""
    remarks: str = ""
    country: str = ""
    country_code: str = ""
    city: str = ""
    asn: str = ""
    latency: Optional[float] = None
    is_working: bool = False
    is_secure: bool = True
    security_issues: List[str] = field(default_factory=list)
    tested_at: str = ""
    details: Optional[Dict[str, Any]] = field(default_factory=dict)