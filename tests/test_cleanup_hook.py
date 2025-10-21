#!/usr/bin/env python3
"""
Tests for cleanup_hook.py module.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.cleanup_hook import main


class TestCleanupHook(unittest.TestCase):
    """Test cases for cleanup_hook.py."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_env = {
            "CERTBOT_DOMAIN": "example.com",
            "CERTBOT_VALIDATION": "test-validation-string",
            "DNSEXIT_API_KEY": "test-api-key",
        }

    def test_missing_domain(self):
        """Test missing CERTBOT_DOMAIN environment variable."""
        with patch.dict(os.environ, {}, clear=True), patch("sys.argv", ["cleanup-hook"]):
            result = main()
            assert result == 1

    def test_missing_validation(self):
        """Test missing CERTBOT_VALIDATION environment variable."""
        env = {"CERTBOT_DOMAIN": "example.com"}
        with patch.dict(os.environ, env, clear=True), patch("sys.argv", ["cleanup-hook"]):
            result = main()
            assert result == 1

    def test_missing_environment_variables(self):
        """Test missing DNSEXIT_API_KEY environment variable."""
        env = {"CERTBOT_DOMAIN": "example.com", "CERTBOT_VALIDATION": "test-validation-string"}
        with patch.dict(os.environ, env, clear=True), patch("sys.argv", ["cleanup-hook"]):
            result = main()
            assert result == 1

    @patch("src.cleanup_hook.DNSExitClient")
    def test_cleanup_hook_success(self, mock_client_class):
        """Test successful cleanup hook execution."""
        mock_client = Mock()
        mock_client.remove_txt_record.return_value = True
        mock_client_class.return_value = mock_client

        with patch.dict(os.environ, self.test_env), patch("sys.argv", ["cleanup-hook"]):
            result = main()
            assert result == 0

        # Verify the client was called correctly
        mock_client.remove_txt_record.assert_called_once_with(
            "example.com", "_acme-challenge.example.com", "test-validation-string"
        )

    @patch("src.cleanup_hook.DNSExitClient")
    def test_cleanup_hook_failure(self, mock_client_class):
        """Test failed cleanup hook execution."""
        mock_client = Mock()
        mock_client.remove_txt_record.return_value = False
        mock_client_class.return_value = mock_client

        with patch.dict(os.environ, self.test_env), patch("sys.argv", ["cleanup-hook"]):
            result = main()
            assert result == 0  # Should not fail for cleanup

    @patch("src.cleanup_hook.DNSExitClient")
    def test_subdomain_handling(self, mock_client_class):
        """Test subdomain handling."""
        mock_client = Mock()
        mock_client.remove_txt_record.return_value = True
        mock_client_class.return_value = mock_client

        env = self.test_env.copy()
        env["CERTBOT_DOMAIN"] = "sub.example.com"

        with patch.dict(os.environ, env), patch("sys.argv", ["cleanup-hook"]):
            result = main()
            assert result == 0

        # Verify subdomain was handled correctly - now using full domain name
        mock_client.remove_txt_record.assert_called_once_with(
            "sub.example.com", "_acme-challenge.sub.example.com", "test-validation-string"
        )

    @patch("src.cleanup_hook.DNSExitClient")
    def test_wildcard_domain_handling(self, mock_client_class):
        """Test wildcard domain handling - specific case for *.example.com."""
        mock_client = Mock()
        mock_client.remove_txt_record.return_value = True
        mock_client_class.return_value = mock_client

        env = self.test_env.copy()
        env["CERTBOT_DOMAIN"] = "example.com"  # This comes from *.example.com wildcard

        with patch.dict(os.environ, env), patch("sys.argv", ["cleanup-hook"]):
            result = main()
            assert result == 0

        # Verify wildcard domain was handled correctly
        # For domain 'example.com', get_domain_parts returns ('', 'example.com')
        # So txt_name should be '_acme-challenge.example.com'
        mock_client.remove_txt_record.assert_called_once_with(
            "example.com", "_acme-challenge.example.com", "test-validation-string"
        )

    @patch("src.cleanup_hook.DNSExitClient")
    def test_logging_level_debug(self, mock_client_class):
        """Test that LOG_LEVEL environment variable is respected."""
        mock_client = Mock()
        mock_client.remove_txt_record.return_value = True
        mock_client_class.return_value = mock_client

        env = self.test_env.copy()
        env["LOG_LEVEL"] = "DEBUG"

        with patch.dict(os.environ, env), patch("sys.argv", ["cleanup-hook"]):
            result = main()
            assert result == 0


if __name__ == "__main__":
    unittest.main()
