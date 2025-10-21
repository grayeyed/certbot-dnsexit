#!/usr/bin/env python3
"""
Behavior-focused tests for DNS propagation functionality in DNSExitClient.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.dnsexit_client import DNSExitClient


class TestDNSPropagation(unittest.TestCase):
    """Behavior-focused test cases for DNS propagation functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = DNSExitClient("test-api-key")
        self.domain = "example.com"
        self.name = "_acme-challenge.example.com"
        self.value = "test-validation-token"
        self.timeout = 10
        self.interval = 5
        self.dns_server = "8.8.8.8"  # Use IP address to avoid DNS resolution

    @patch("dns.resolver.Resolver")
    def test_wait_for_propagation_success(self, mock_resolver_class):
        """Test successful DNS propagation detection."""
        mock_resolver_instance = mock_resolver_class.return_value
        mock_resolver_instance.resolve.return_value = [MagicMock(strings=[self.value.encode("utf-8")])]

        result = self.client.wait_for_propagation(
            self.domain, self.name, self.value, timeout=5, check_interval=2, dns_server=self.dns_server
        )

        assert result

    @patch("dns.resolver.Resolver")
    def test_wait_for_propagation_wrong_value(self, mock_resolver_class):
        """Test propagation fails when TXT value doesn't match."""
        mock_resolver_instance = mock_resolver_class.return_value
        mock_resolver_instance.resolve.return_value = [MagicMock(strings=[b"different-value"])]

        result = self.client.wait_for_propagation(
            self.domain, self.name, self.value, timeout=5, check_interval=2, dns_server=self.dns_server
        )

        assert not result

    @patch("dns.resolver.Resolver")
    def test_wait_for_propagation_nxdomain(self, mock_resolver_class):
        """Test propagation fails when DNS record doesn't exist."""
        from dns.resolver import NXDOMAIN

        mock_resolver_instance = mock_resolver_class.return_value
        mock_resolver_instance.resolve.side_effect = NXDOMAIN()

        result = self.client.wait_for_propagation(
            self.domain, self.name, self.value, timeout=5, check_interval=2, dns_server=self.dns_server
        )

        assert not result

    @patch("dns.resolver.Resolver")
    def test_wait_for_propagation_no_answer(self, mock_resolver_class):
        """Test propagation fails when DNS server returns no answer."""
        from dns.resolver import NoAnswer

        mock_resolver_instance = mock_resolver_class.return_value
        mock_resolver_instance.resolve.side_effect = NoAnswer()

        result = self.client.wait_for_propagation(
            self.domain, self.name, self.value, timeout=5, check_interval=2, dns_server=self.dns_server
        )

        assert not result

    @patch("dns.resolver.Resolver")
    def test_wait_for_propagation_timeout(self, mock_resolver_class):
        """Test propagation timeout behavior."""
        from dns.resolver import NXDOMAIN

        mock_resolver_instance = mock_resolver_class.return_value
        mock_resolver_instance.resolve.side_effect = NXDOMAIN()  # Simulate record not found

        result = self.client.wait_for_propagation(
            self.domain, self.name, self.value, timeout=0.1, check_interval=0.01, dns_server=self.dns_server
        )

        assert not result

    @patch("dns.resolver.Resolver")
    def test_wait_for_propagation_multiple_txt_records(self, mock_resolver_class):
        """Test propagation succeeds with multiple TXT records."""
        mock_resolver_instance = mock_resolver_class.return_value
        mock_resolver_instance.resolve.return_value = [
            MagicMock(strings=[b"other-value"]),
            MagicMock(strings=[self.value.encode("utf-8")]),
        ]

        result = self.client.wait_for_propagation(
            self.domain, self.name, self.value, timeout=5, check_interval=2, dns_server=self.dns_server
        )

        assert result

    @patch("dns.resolver.Resolver")
    def test_wait_for_propagation_dns_timeout(self, mock_resolver_class):
        """Test propagation fails on DNS query timeout."""
        from dns.exception import Timeout

        mock_resolver_instance = mock_resolver_class.return_value
        mock_resolver_instance.resolve.side_effect = Timeout()

        result = self.client.wait_for_propagation(
            self.domain, self.name, self.value, timeout=5, check_interval=2, dns_server=self.dns_server
        )

        assert not result

    @patch("dns.resolver.Resolver")
    def test_wait_for_propagation_general_exception(self, mock_resolver_class):
        """Test propagation fails on general DNS exception."""
        mock_resolver_instance = mock_resolver_class.return_value
        mock_resolver_instance.resolve.side_effect = Exception("DNS server error")

        result = self.client.wait_for_propagation(
            self.domain, self.name, self.value, timeout=5, check_interval=2, dns_server=self.dns_server
        )

        assert not result

    @patch("dns.resolver.Resolver")
    @patch("dns.resolver.resolve")
    def test_wait_for_propagation_custom_dns_server_param_hostname(self, mock_resolve, mock_resolver_class):
        """Test propagation with custom DNS server hostname."""
        mock_resolver_instance = mock_resolver_class.return_value
        mock_resolver_instance.resolve.return_value = [MagicMock(strings=[self.value.encode("utf-8")])]

        # Mock DNS server hostname resolution to return IP address
        mock_resolve.return_value = [MagicMock(address="192.0.2.10")]

        result = self.client.wait_for_propagation(
            self.domain, self.name, self.value, timeout=5, check_interval=2, dns_server="custom.dns.server"
        )

        assert result

    @patch("dns.resolver.Resolver")
    def test_wait_for_propagation_unicode_value(self, mock_resolver_class):
        """Test propagation with unicode TXT record values."""
        mock_resolver_instance = mock_resolver_class.return_value
        unicode_value = "test-unicode-значение"
        mock_resolver_instance.resolve.return_value = [MagicMock(strings=[unicode_value.encode("utf-8")])]

        result = self.client.wait_for_propagation(
            self.domain, self.name, unicode_value, timeout=5, check_interval=2, dns_server=self.dns_server
        )

        assert result


if __name__ == "__main__":
    unittest.main()
