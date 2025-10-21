#!/usr/bin/env python3
"""
Certbot authentication hook for DNS-01 challenge with DNS Exit.
This script is called by certbot to add the TXT record for DNS-01 validation.
"""

import os
import sys
import time

from dnsexit_client import DNSExitClient, configure_logger
from logging_config import log_component_error, log_dns_operation, setup_logger

# Configure logging with environment variable support
logger = setup_logger(__name__)

# Debug: Log the current LOG_LEVEL
current_log_level = os.environ.get("LOG_LEVEL", "NOT_SET")
logger.debug(f"Current LOG_LEVEL environment variable: {current_log_level}")


def main():
    """
    Main entry point for the auth hook.

    Environment variables provided by certbot:
    - CERTBOT_DOMAIN: The domain being validated
    - CERTBOT_VALIDATION: The validation string to add as TXT record
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

        log_dns_operation(logger, "challenge start", domain, "creating TXT record")
        # Note: Not logging validation value for security reasons

        # Add the TXT record
        if not client.add_txt_record(domain, txt_name, validation):
            log_component_error(logger, "auth_hook", f"Failed to add TXT record for {domain}")
            return 1
        log_dns_operation(logger, "record added", domain, "success")

        # Get DNS propagation wait time from environment variable
        dns_propagation_wait = int(os.environ.get("DNS_PROPAGATION_WAIT", "300"))
        logger.info(f"Waiting for DNS propagation (timeout: {dns_propagation_wait}s)...")

        # Get DNS propagation check interval from environment variable
        dns_propagation_check_interval = int(os.environ.get("DNS_PROPAGATION_CHECK_INTERVAL", "15"))
        logger.info(f"DNS propagation check interval: {dns_propagation_check_interval}s")

        # Get DNS Exit DNS server from environment variable
        dns_server = os.environ.get("DNS_PROPAGATION_ADDRESS", "ns12.dnsexit.com")

        # Use the unified function for periodic propagation checking with retries
        propagation_result = client.wait_for_propagation(
            domain,
            txt_name,
            validation,
            timeout=dns_propagation_wait,
            dns_server=dns_server,
            retry_on_failure=True,
            check_interval=dns_propagation_check_interval,
        )

        if propagation_result:
            log_dns_operation(logger, "propagation", domain, "completed successfully")

            # Additional pause for complete DNS synchronization across all servers
            # This helps prevent Let's Encrypt secondary validation failures
            dns_finalization_wait = int(os.environ.get("DNS_FINALIZATION_WAIT", "5"))  # 5 seconds default
            logger.info(f"Waiting additional {dns_finalization_wait}s for complete DNS synchronization...")
            time.sleep(dns_finalization_wait)

            return 0
        log_component_error(logger, "auth_hook", f"DNS record did not propagate within timeout for {domain}")
        return 1

    except Exception as e:
        logger.exception(f"Error in auth hook: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
