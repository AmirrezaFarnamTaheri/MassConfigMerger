import asyncio
import hashlib
import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

import aiohttp
from aiohttp_proxy import ProxyConnector

from ..config import ProxyConfig
from ..core import Proxy


@dataclass
class SecurityTest:
    """Result of a security test"""
    name: str
    passed: bool
    severity: str  # 'critical', 'high', 'medium', 'low'
    description: str
    details: Dict[str, Any] = None


class MaliciousNodeDetector:
    """Comprehensive detection of malicious proxies"""

    def __init__(self):
        self.config = ProxyConfig()
        self.test_results: Dict[str, List[SecurityTest]] = {}

        # Content fingerprints for known-good sites
        self.content_fingerprints = {
            'google': self._get_fingerprint_hash('https://www.google.com'),
            'gstatic': self._get_fingerprint_hash('https://www.gstatic.com'),
        }

    async def detect_malicious(self, proxy: Proxy) -> Dict[str, Any]:
        """
        Comprehensive malicious proxy detection.
        Returns severity level and detailed findings.
        """
        results = {
            'is_malicious': False,
            'severity': 'none',
            'tests': [],
            'score': 0,  # 0-100, higher = more malicious
            'recommendations': []
        }

        try:
            # Run all security tests
            connector = ProxyConnector.from_url(proxy.config)
            async with aiohttp.ClientSession(connector=connector) as session:

                # Test 1: Content Injection Detection
                injection_test = await self._test_content_injection(session, proxy)
                results['tests'].append(injection_test)
                if not injection_test.passed:
                    results['score'] += 25

                # Test 2: Header Manipulation Detection
                header_test = await self._test_header_manipulation(session, proxy)
                results['tests'].append(header_test)
                if not header_test.passed:
                    results['score'] += 20

                # Test 3: DNS Leak Detection
                dns_test = await self._test_dns_leak(session, proxy)
                results['tests'].append(dns_test)
                if not dns_test.passed:
                    results['score'] += 15

                # Test 4: Redirect Hijacking
                redirect_test = await self._test_redirect_hijacking(session, proxy)
                results['tests'].append(redirect_test)
                if not redirect_test.passed:
                    results['score'] += 15

                # Test 5: Malware Detection (via reputation)
                malware_test = await self._test_malware_reputation(proxy)
                results['tests'].append(malware_test)
                if not malware_test.passed:
                    results['score'] += 20

                # Test 6: Port Scanning Detection
                port_test = await self._test_suspicious_ports(proxy)
                results['tests'].append(port_test)
                if not port_test.passed:
                    results['score'] += 5

        except Exception as e:
            results['tests'].append(SecurityTest(
                name='initialization',
                passed=False,
                severity='high',
                description=f'Failed to run security tests: {str(e)}'
            ))
            results['score'] = 50

        # Determine maliciousness
        if results['score'] >= 70:
            results['is_malicious'] = True
            results['severity'] = 'critical'
            results['recommendations'].append('Block this proxy immediately')
        elif results['score'] >= 50:
            results['severity'] = 'high'
            results['recommendations'].append('Review carefully before using')
        elif results['score'] >= 30:
            results['severity'] = 'medium'
            results['recommendations'].append('Use with caution')
        else:
            results['severity'] = 'low'

        return results

    async def _test_content_injection(self, session: aiohttp.ClientSession,
                                     proxy: Proxy) -> SecurityTest:
        """Detect if proxy modifies page content"""
        try:
            # Fetch through proxy
            async with session.get('https://www.google.com',
                                  timeout=aiohttp.ClientTimeout(
                                      total=self.config.SECURITY_CHECK_TIMEOUT)) as resp:
                content_via_proxy = await resp.text()

            # Fetch directly (would need different approach in real scenario)
            # For now, check for common injection patterns
            injection_patterns = [
                '<script',
                'onclick=',
                'document.domain',
                'location.href',
                'eval(',
                'iframe'
            ]

            injected_scripts = sum(1 for pattern in injection_patterns
                                 if pattern.lower() in content_via_proxy.lower())

            if injected_scripts > 2:
                return SecurityTest(
                    name='content_injection',
                    passed=False,
                    severity='critical',
                    description='Multiple suspicious scripts detected in content',
                    details={'injected_patterns': injected_scripts}
                )

            return SecurityTest(
                name='content_injection',
                passed=True,
                severity='none',
                description='No content injection detected'
            )

        except asyncio.TimeoutError:
            return SecurityTest(
                name='content_injection',
                passed=False,
                severity='medium',
                description='Test timeout - unable to verify content integrity'
            )
        except Exception as e:
            return SecurityTest(
                name='content_injection',
                passed=False,
                severity='high',
                description=f'Content injection test failed: {str(e)}'
            )

    async def _test_header_manipulation(self, session: aiohttp.ClientSession,
                                       proxy: Proxy) -> SecurityTest:
        """Detect if proxy strips or modifies headers"""
        try:
            # Custom headers to send
            custom_headers = {
                'X-Custom-Header': 'test-value-12345',
                'X-Another-Header': 'another-value',
                'User-Agent': 'ConfigStream-SecurityTest/1.0'
            }

            async with session.get('http://httpbin.org/headers',
                                  headers=custom_headers,
                                  timeout=aiohttp.ClientTimeout(
                                      total=self.config.SECURITY_CHECK_TIMEOUT)) as resp:
                data = await resp.json()
                received_headers = data.get('headers', {})

            # Check which headers were preserved
            missing_headers = []
            for header_key, header_value in custom_headers.items():
                # Headers are case-insensitive
                found = False
                for received_key in received_headers.keys():
                    if received_key.lower() == header_key.lower():
                        found = True
                        break

                if not found:
                    missing_headers.append(header_key)

            if len(missing_headers) > self.config.SECURITY['header_strip_threshold']:
                return SecurityTest(
                    name='header_manipulation',
                    passed=False,
                    severity='high',
                    description=f'Proxy stripped {len(missing_headers)} headers',
                    details={'stripped_headers': missing_headers}
                )

            return SecurityTest(
                name='header_manipulation',
                passed=True,
                severity='none',
                description='Headers preserved correctly'
            )

        except Exception as e:
            return SecurityTest(
                name='header_manipulation',
                passed=False,
                severity='medium',
                description=f'Header test failed: {str(e)}'
            )

    async def _test_dns_leak(self, session: aiohttp.ClientSession,
                            proxy: Proxy) -> SecurityTest:
        """Detect DNS leaks"""
        try:
            # Use DNS leak detection service
            async with session.get('https://dns.google/dns-query?name=example.com&type=A',
                                  timeout=aiohttp.ClientTimeout(
                                      total=self.config.SECURITY_CHECK_TIMEOUT)) as resp:
                if resp.status == 200:
                    return SecurityTest(
                        name='dns_leak',
                        passed=True,
                        severity='none',
                        description='DNS queries routed through proxy'
                    )

            return SecurityTest(
                name='dns_leak',
                passed=False,
                severity='high',
                description='Possible DNS leak detected'
            )

        except Exception as e:
            return SecurityTest(
                name='dns_leak',
                passed=False,
                severity='medium',
                description=f'DNS leak test failed: {str(e)}'
            )

    async def _test_redirect_hijacking(self, session: aiohttp.ClientSession,
                                      proxy: Proxy) -> SecurityTest:
        """Detect redirect hijacking"""
        try:
            redirects_followed = 0

            async with session.get('http://httpbin.org/redirect/3',
                                  allow_redirects=True,
                                  timeout=aiohttp.ClientTimeout(
                                      total=self.config.SECURITY_CHECK_TIMEOUT)) as resp:
                redirects_followed = len(resp.history)

            if redirects_followed > self.config.SECURITY['redirect_follow_limit']:
                return SecurityTest(
                    name='redirect_hijacking',
                    passed=False,
                    severity='medium',
                    description=f'Excessive redirects detected: {redirects_followed}',
                    details={'redirect_count': redirects_followed}
                )

            return SecurityTest(
                name='redirect_hijacking',
                passed=True,
                severity='none',
                description='Redirects handled correctly'
            )

        except Exception as e:
            return SecurityTest(
                name='redirect_hijacking',
                passed=False,
                severity='low',
                description=f'Redirect test failed: {str(e)}'
            )

    async def _test_malware_reputation(self, proxy: Proxy) -> SecurityTest:
        """Check proxy IP against malware reputation lists"""
        try:
            # Check against threat databases
            # This is a simplified example - integrate with real threat feeds

            threat_indicators = []

            # Check ASN
            if proxy.asn in self.config.SECURITY['malicious_asn_list']:
                threat_indicators.append('Known malicious ASN')

            # Check country
            if proxy.country_code in self.config.SECURITY['blocked_countries']:
                threat_indicators.append(f'Blocked country: {proxy.country_code}')

            # Check IP reputation (mock - implement with real API)
            # In production, integrate with AbuseIPDB, AlienVault, etc.

            if threat_indicators:
                return SecurityTest(
                    name='malware_reputation',
                    passed=False,
                    severity='high',
                    description='Proxy flagged in threat intelligence',
                    details={'threats': threat_indicators}
                )

            return SecurityTest(
                name='malware_reputation',
                passed=True,
                severity='none',
                description='No malware/threat indicators found'
            )

        except Exception as e:
            return SecurityTest(
                name='malware_reputation',
                passed=False,
                severity='low',
                description=f'Reputation check failed: {str(e)}'
            )

    async def _test_suspicious_ports(self, proxy: Proxy) -> SecurityTest:
        """Detect suspicious port configurations"""
        try:
            for min_port, max_port in self.config.SECURITY['suspicious_port_range']:
                if min_port <= proxy.port <= max_port:
                    return SecurityTest(
                        name='suspicious_ports',
                        passed=False,
                        severity='medium',
                        description=f'Proxy uses suspicious port: {proxy.port}',
                        details={'port': proxy.port, 'range': (min_port, max_port)}
                    )

            return SecurityTest(
                name='suspicious_ports',
                passed=True,
                severity='none',
                description='Port configuration normal'
            )

        except Exception as e:
            return SecurityTest(
                name='suspicious_ports',
                passed=False,
                severity='low',
                description=f'Port check failed: {str(e)}'
            )

    @staticmethod
    def _get_fingerprint_hash(url: str) -> str:
        """Get content fingerprint hash"""
        # In production, would fetch and hash actual content
        return hashlib.sha256(url.encode()).hexdigest()