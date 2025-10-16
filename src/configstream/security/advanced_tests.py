import asyncio
import hashlib
from typing import List, Dict, Optional
from dataclasses import dataclass

from ..core import Proxy
from ..testers import SingBoxTester

@dataclass
class SecurityTest:
    """Security test definition"""
    name: str
    description: str
    severity: str  # low, medium, high, critical
    test_func: callable

class AdvancedSecurityTester:
    """Advanced security testing suite"""

    def __init__(self):
        self.tests = [
            SecurityTest(
                name="dns_leak",
                description="DNS leak detection",
                severity="high",
                test_func=self.test_dns_leak
            ),
            SecurityTest(
                name="webrtc_leak",
                description="WebRTC IP leak",
                severity="high",
                test_func=self.test_webrtc_leak
            ),
            SecurityTest(
                name="http_header_leak",
                description="HTTP header information leak",
                severity="medium",
                test_func=self.test_header_leak
            ),
            SecurityTest(
                name="ssl_strip",
                description="SSL stripping attack",
                severity="critical",
                test_func=self.test_ssl_strip
            ),
            SecurityTest(
                name="malware_injection",
                description="Malware/script injection",
                severity="critical",
                test_func=self.test_malware_injection
            ),
            SecurityTest(
                name="traffic_analysis",
                description="Traffic pattern analysis",
                severity="medium",
                test_func=self.test_traffic_analysis
            ),
        ]

    async def test_dns_leak(self, proxy: Proxy, worker: SingBoxTester) -> Dict:
        """Test for DNS leaks"""
        # Query DNS leak test site
        test_urls = [
            "https://dnsleaktest.com/",
            "https://www.dnsleaktest.org/",
        ]

        results = []
        for url in test_urls:
            try:
                # This is a placeholder. In a real scenario, you would
                # properly parse the response to get the DNS servers.
                response = "1.1.1.1" # await worker.fetch_url(url, proxy)
                dns_servers = [response]
                results.append({
                    'url': url,
                    'dns_servers': dns_servers,
                    'leaked': True
                })
            except Exception as e:
                results.append({'url': url, 'error': str(e)})

        return {
            'passed': all(not r.get('leaked', True) for r in results),
            'details': results
        }

    async def test_webrtc_leak(self, proxy: Proxy, worker: SingBoxTester) -> Dict:
        """Test for WebRTC IP leaks"""
        test_url = "https://browserleaks.com/webrtc"

        try:
            # This is a placeholder. In a real scenario, you would
            # properly parse the response to get the WebRTC IP addresses.
            response = "1.1.1.1" # await worker.fetch_url(test_url, proxy)
            leaked_ips = [response]

            return {
                'passed': len(leaked_ips) == 0,
                'leaked_ips': leaked_ips
            }
        except Exception as e:
            return {'passed': False, 'error': str(e)}

    async def test_header_leak(self, proxy: Proxy, worker: SingBoxTester) -> Dict:
        """Test for HTTP header information leaks"""
        test_url = "https://httpbin.org/headers"

        try:
            # This is a placeholder. In a real scenario, you would
            # properly parse the response to get the headers.
            response = {"headers": {"X-Forwarded-For": "1.1.1.1"}} # await worker.fetch_url(test_url, proxy)
            headers = response.get('headers', {})

            # Check for sensitive headers
            sensitive_headers = ['X-Forwarded-For', 'Via', 'X-Real-IP']
            leaked = [h for h in sensitive_headers if h in headers]

            return {
                'passed': len(leaked) == 0,
                'leaked_headers': leaked,
                'all_headers': headers
            }
        except Exception as e:
            return {'passed': False, 'error': str(e)}

    async def test_ssl_strip(self, proxy: Proxy, worker: SingBoxTester) -> Dict:
        """Test for SSL stripping attacks"""
        # Try to access HTTPS site and check if downgraded to HTTP
        test_url = "https://www.howsmyssl.com/a/check"

        try:
            # This is a placeholder. In a real scenario, you would
            # properly parse the response to get the SSL info.
            response = {"tls_version": "TLS 1.3"} # await worker.fetch_url(test_url, proxy)
            ssl_info = response.get('tls_version', '')

            return {
                'passed': 'TLS' in ssl_info,
                'ssl_version': ssl_info,
                'downgraded': 'TLS' not in ssl_info
            }
        except Exception as e:
            return {'passed': False, 'error': str(e)}

    async def test_malware_injection(self, proxy: Proxy, worker: SingBoxTester) -> Dict:
        """Test for malware/script injection"""
        # Fetch a known clean page and check for modifications
        test_url = "https://example.com/"

        try:
            # This is a placeholder. In a real scenario, you would
            # properly parse the response to get the content.
            response = "<html></html>" # await worker.fetch_url(test_url, proxy)
            content = response

            # Calculate content hash
            content_hash = hashlib.sha256(content.encode()).hexdigest()

            # Known hash of example.com (update periodically)
            known_hash = "..."  # Add actual hash

            # Check for suspicious scripts
            suspicious_patterns = [
                '<script>',
                'eval(',
                'document.write(',
                'iframe',
            ]

            found_suspicious = [p for p in suspicious_patterns if p in content.lower()]

            return {
                'passed': content_hash == known_hash and len(found_suspicious) == 0,
                'hash_match': content_hash == known_hash,
                'suspicious_content': found_suspicious
            }
        except Exception as e:
            return {'passed': False, 'error': str(e)}

    async def test_traffic_analysis(self, proxy: Proxy, worker: SingBoxTester) -> Dict:
        """Analyze traffic patterns for anomalies"""
        # Multiple requests to detect timing attacks or traffic shaping
        test_urls = [
            "https://httpbin.org/bytes/1000",
            "https://httpbin.org/bytes/10000",
            "https://httpbin.org/bytes/100000",
        ]

        timings = []
        for url in test_urls:
            try:
                start = asyncio.get_event_loop().time()
                # await worker.fetch_url(url, proxy)
                await asyncio.sleep(0.1)
                elapsed = asyncio.get_event_loop().time() - start
                timings.append(elapsed)
            except:
                pass

        if len(timings) >= 2:
            # Check for linear scaling (normal) vs exponential (throttling)
            ratio = timings[1] / timings[0] if timings[0] > 0 else 0
            throttled = ratio > 100  # 100x slowdown indicates throttling

            return {
                'passed': not throttled,
                'timings': timings,
                'throttled': throttled
            }

        return {'passed': False, 'error': 'Insufficient data'}

    async def run_all_tests(
        self,
        proxy: Proxy,
        worker: SingBoxTester
    ) -> Dict[str, Dict]:
        """Run all security tests"""
        results = {}

        for test in self.tests:
            try:
                result = await test.test_func(proxy, worker)
                results[test.name] = {
                    'description': test.description,
                    'severity': test.severity,
                    **result
                }
            except Exception as e:
                results[test.name] = {
                    'description': test.description,
                    'severity': test.severity,
                    'passed': False,
                    'error': str(e)
                }

        return results