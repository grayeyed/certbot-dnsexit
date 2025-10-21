#!/usr/bin/env python3
"""
Tests for logging_config.py module.
"""

import logging
import os
import sys
import unittest
from unittest.mock import patch

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.logging_config import get_log_level_from_env, setup_logger


class TestLoggingConfig(unittest.TestCase):
    """Test cases for logging_config.py."""

    def test_get_log_level_from_env_default(self):
        """Test get_log_level_from_env with no environment variable set."""
        with patch.dict(os.environ, {}, clear=True):
            level = get_log_level_from_env()
            assert level == logging.INFO

    def test_get_log_level_from_env_debug(self):
        """Test get_log_level_from_env with DEBUG level."""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            level = get_log_level_from_env()
            assert level == logging.DEBUG

    def test_get_log_level_from_env_info(self):
        """Test get_log_level_from_env with INFO level."""
        with patch.dict(os.environ, {"LOG_LEVEL": "INFO"}):
            level = get_log_level_from_env()
            assert level == logging.INFO

    def test_get_log_level_from_env_warning(self):
        """Test get_log_level_from_env with WARNING level."""
        with patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}):
            level = get_log_level_from_env()
            assert level == logging.WARNING

    def test_get_log_level_from_env_error(self):
        """Test get_log_level_from_env with ERROR level."""
        with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}):
            level = get_log_level_from_env()
            assert level == logging.ERROR

    def test_get_log_level_from_env_critical(self):
        """Test get_log_level_from_env with CRITICAL level."""
        with patch.dict(os.environ, {"LOG_LEVEL": "CRITICAL"}):
            level = get_log_level_from_env()
            assert level == logging.CRITICAL

    def test_get_log_level_from_env_case_insensitive(self):
        """Test get_log_level_from_env is case insensitive."""
        with patch.dict(os.environ, {"LOG_LEVEL": "debug"}):
            level = get_log_level_from_env()
            assert level == logging.DEBUG

        with patch.dict(os.environ, {"LOG_LEVEL": "Debug"}):
            level = get_log_level_from_env()
            assert level == logging.DEBUG

    def test_get_log_level_from_env_invalid_level(self):
        """Test get_log_level_from_env with invalid level falls back to default."""
        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}):
            level = get_log_level_from_env(logging.WARNING)
            assert level == logging.WARNING

    def test_get_log_level_from_env_empty_string(self):
        """Test get_log_level_from_env with empty string falls back to default."""
        with patch.dict(os.environ, {"LOG_LEVEL": ""}):
            level = get_log_level_from_env(logging.ERROR)
            assert level == logging.ERROR

    def test_setup_logger_with_env_level(self):
        """Test setup_logger uses environment variable for log level."""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            logger = setup_logger("test_logger")
            assert logger.level == logging.DEBUG

    def test_setup_logger_with_explicit_level(self):
        """Test setup_logger uses explicit level parameter over environment."""
        with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}):
            logger = setup_logger("test_logger", level=logging.DEBUG)
            assert logger.level == logging.DEBUG

    def test_setup_logger_no_env_var(self):
        """Test setup_logger uses INFO as default when no environment variable."""
        with patch.dict(os.environ, {}, clear=True):
            logger = setup_logger("test_logger")
            assert logger.level == logging.INFO


if __name__ == "__main__":
    unittest.main()
