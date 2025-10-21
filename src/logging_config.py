#!/usr/bin/env python3
"""
Unified logging configuration for DNS Exit Certbot scripts.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime

# Standardized logging formats
LOG_FORMAT_STANDARD = "[%(asctime)s] [%(levelname)s] %(message)s"
LOG_FORMAT_JSON = '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""

    def __init__(self, use_json: bool = False):
        super().__init__()
        self.use_json = use_json

    def format(self, record):
        if self.use_json:
            # Create structured JSON log entry
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }

            # Add exception info if present
            if record.exc_info:
                log_entry["exception"] = self.formatException(record.exc_info)

            # Add extra fields if present
            for key, value in record.__dict__.items():
                if key not in [
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                ]:
                    log_entry[key] = value

            return json.dumps(log_entry, ensure_ascii=False)
        return super().format(record)


def get_log_level_from_env(default_level: int = logging.INFO) -> int:
    """
    Get logging level from environment variable.

    Args:
        default_level: Default logging level if environment variable not set

    Returns:
        Logging level constant
    """
    log_level_str = os.environ.get("LOG_LEVEL", "").upper()

    level_mapping = {
        "QUIET": logging.ERROR,  # QUIET = only errors and above
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    if log_level_str in level_mapping:
        return level_mapping[log_level_str]

    return default_level


def setup_logger(
    name: str,
    log_file: str | None = None,
    level: int | None = None,
    use_json: bool = False,
    operation_id: str | None = None,
    component: str | None = None,
) -> logging.Logger:
    """
    Set up a unified logger with consistent formatting.

    Args:
        name: Logger name
        log_file: Optional log file path
        level: Logging level (if None, will be determined from environment)
        use_json: Whether to use JSON formatting
        operation_id: Optional operation ID for correlation

    Returns:
        Configured logger instance
    """
    # If level is not specified, get it from environment
    if level is None:
        level = get_log_level_from_env(logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear any existing handlers
    logger.handlers.clear()

    # Create formatter
    if use_json:
        formatter = StructuredFormatter(use_json=True)
    else:
        formatter = logging.Formatter(LOG_FORMAT_STANDARD, datefmt="%Y-%m-%d %H:%M:%S")

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if log_file is provided
    if log_file:
        # Ensure directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Add operation_id and component to logger if provided
    extra = {}
    if operation_id:
        extra["operation_id"] = operation_id
    if component:
        extra["component"] = component

    if extra:
        logger = logging.LoggerAdapter(logger, extra)

    return logger


def setup_structured_logger(
    name: str, log_file: str | None = None, level: int | None = None, operation_id: str | None = None
) -> logging.Logger:
    """
    Set up a structured JSON logger for better log analysis.

    Args:
        name: Logger name
        log_file: Optional log file path
        level: Logging level (if None, will be determined from environment)
        operation_id: Optional operation ID for correlation

    Returns:
        Configured structured logger instance
    """
    return setup_logger(name, log_file, level, use_json=True, operation_id=operation_id)


def log_error_and_exit(logger: logging.Logger, message: str, exit_code: int = 1) -> None:
    """
    Log an error message and exit the program.

    Args:
        logger: Logger instance
        message: Error message
        exit_code: Exit code (default: 1)
    """
    logger.error(message)
    sys.exit(exit_code)


def log_exception(logger: logging.Logger, message: str, exit_code: int = 1) -> None:
    """
    Log an exception with full traceback and exit.

    Args:
        logger: Logger instance
        message: Error message
        exit_code: Exit code (default: 1)
    """
    logger.exception(message)
    sys.exit(exit_code)


# Central logger functions (replacement for central_logger.py)
def log_certbot_start(logger: logging.Logger, domains: str, email: str) -> None:
    """Log certificate process start."""
    logger.info(f"Starting certificate process for domains: {domains}, email: {email}")


def log_dns_operation(logger: logging.Logger, operation: str, domain: str, status: str) -> None:
    """Log DNS operation."""
    logger.info(f"DNS {operation} for {domain}: {status}")


def log_certificate_issued(logger: logging.Logger, domain: str, expiry_date: str) -> None:
    """Log successful certificate issuance."""
    logger.info(f"Certificate issued for {domain}, expires: {expiry_date}")


def log_component_error(logger: logging.Logger, component: str, message: str) -> None:
    """Log error with component identification."""
    logger.error(f"[{component}] {message}")


def log_component_warning(logger: logging.Logger, component: str, message: str) -> None:
    """Log warning with component identification."""
    logger.warning(f"[{component}] {message}")


class LogContext:
    """Context manager for adding structured context to logs."""

    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
        self.original_extra = getattr(logger, "extra", {})

    def __enter__(self):
        # Add context to logger
        if hasattr(self.logger, "logger"):
            # LoggerAdapter case
            self.logger.logger = logging.LoggerAdapter(
                self.logger.logger, {**getattr(self.logger.logger, "extra", {}), **self.context}
            )
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Remove context (simplified approach)
        pass
