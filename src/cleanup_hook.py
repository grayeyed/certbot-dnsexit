#!/usr/bin/env python3
"""
Certbot cleanup hook for DNS-01 challenge with DNS Exit.
This script is called by certbot to remove the TXT record after DNS-01 validation.
"""

import os
import sys

from logging_config import setup_logger

# Configure logging with environment variable support
logger = setup_logger(__name__)

# Import DNSExit client and config loader after logger setup
from dnsexit_client import DNSExitClient, configure_logger

# Debug: Log the current LOG_LEVEL
current_log_level = os.environ.get("LOG_LEVEL", "NOT_SET")
logger.debug(f"Current LOG_LEVEL environment variable: {current_log_level}")


def main():
    """
    Main entry point for the cleanup hook.

    Environment variables provided by certbot:
    - CERTBOT_DOMAIN: The domain being validated
    - CERTBOT_VALIDATION: The validation string to remove from TXT record
    - LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """

    try:
        # Configure DNSExit client logger to match our logger configuration
        configure_logger(logger)

        # Validate required environment variables
        domain = os.environ.get("CERTBOT_DOMAIN")
        validation = os.environ.get("CERTBOT_VALIDATION")
        api_key = os.environ.get("DNSEXIT_API_KEY")

        if not all([domain, validation, api_key]):
            missing = []
            if not domain:
                missing.append("CERTBOT_DOMAIN")
            if not validation:
                missing.append("CERTBOT_VALIDATION")
            if not api_key:
                missing.append("DNSEXIT_API_KEY")
            logger.error(f"Missing required environment variables: {', '.join(missing)}")
            return 1

        # Initialize DNS Exit client
        client = DNSExitClient(api_key)

        # For DNS-01 challenge, the TXT record name is always _acme-challenge.{domain}
        # where domain is the fully qualified domain name being validated
        txt_name = f"_acme-challenge.{domain}"

        logger.info(f"Removing TXT record for domain: {domain}")
        logger.info(f"TXT record name: {txt_name}")
        # Note: Not logging validation value for security reasons

        # Remove the TXT record
        if not client.remove_txt_record(domain, txt_name, validation):
            logger.warning("Failed to remove TXT record (continuing cleanup)")

        logger.info("DNS record cleanup completed")
        return 0

    except Exception as e:
        logger.exception(f"Error in cleanup hook: {e}")
        return 0  # Don't fail cleanup due to errors


if __name__ == "__main__":
    sys.exit(main())
