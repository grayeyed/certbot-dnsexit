#!/usr/bin/env python3
"""
DNS Exit API client for managing DNS records.
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any, TypedDict

import requests

if TYPE_CHECKING:
    import dns

# Get module logger
logger = logging.getLogger(__name__)


def configure_logger(main_logger=None):
    """Configure the DNSExit client logger to match main logger configuration."""
    if main_logger is not None:
        # Copy level from main logger
        logger.setLevel(main_logger.level)
        # Copy handlers from main logger
        for handler in main_logger.handlers:
            logger.addHandler(handler)
    # If no main logger specified, let it inherit from parent


# Module-level constants
DEFAULT_BASE_URL = "https://api.dnsexit.com/dns/"
DEFAULT_USER_AGENT = "Certbot-DNSExit/1.0"
REQUEST_TIMEOUT = (30, 30)  # (connect_timeout, read_timeout)
RESOLVER_TIMEOUT = 5
MIN_PROPAGATION_INTERVAL = 5


class DNSExitResponse(TypedDict, total=False):
    code: int
    message: str
    data: dict[str, Any]


class DNSExitClient:
    """Client for interacting with DNS Exit API."""

    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL):
        """
        Initialize the DNS Exit client.

        Args:
            api_key: DNS Exit API key
            base_url: Base URL for DNS Exit API
        """
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()

        # Configure SSL/TLS settings for better compatibility
        self.session.verify = True  # Verify SSL certificates
        self.session.headers.update({"Content-Type": "application/json"})
        # Important: requests doesn't use Session.timeout; pass timeout per call

    def _safe_serialize(self, obj: Any) -> str:
        """
        Safely serialize an object to JSON string, handling mock objects and other types.

        Args:
            obj: Object to serialize

        Returns:
            JSON string representation (truncated if too long)
        """
        try:
            # Check if this is a mock object (common in tests)
            # Try JSON first for common containers
            try:
                serialized = json.dumps(obj, ensure_ascii=False)
            except Exception:
                # Fallback to string representation
                serialized = str(obj)
            # Truncate very long strings to prevent log spam
            if isinstance(serialized, str) and len(serialized) > 1000:
                return serialized[:1000] + "...[truncated]"
            return serialized
        except Exception:
            return str(obj)

    def _mask_sensitive_data(self, data: Any) -> Any:
        """
        Mask sensitive data like API keys, secrets, and passwords in data structures.

        Args:
            data: Data structure to mask (dict, list, or primitive)

        Returns:
            Data with sensitive fields masked
        """
        if isinstance(data, dict):
            masked = {}
            for key, value in data.items():
                # Mask fields that likely contain sensitive data
                if any(sensitive in key.lower() for sensitive in ["key", "secret", "password", "token", "auth"]):
                    masked[key] = "***MASKED***"
                else:
                    # Recursively mask nested structures
                    masked[key] = self._mask_sensitive_data(value)
            return masked
        if isinstance(data, list):
            return [self._mask_sensitive_data(item) for item in data]
        return data

    def _make_request(
        self,
        method: str,
        base_url: str | None = None,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> DNSExitResponse | None:
        """
        Make an API request to DNS Exit.

        Args:
            method: HTTP method (GET, POST)
            base_url: Optional API endpoint override (defaults to self.base_url)
            params: Query parameters (for GET or POST overrides like apikey/domain)
            data: Request body data (JSON for POST)

        Returns:
            Parsed JSON response or None if error
        """
        url = base_url or self.base_url

        # Prepare params and ensure API key is present
        if params is None:
            request_params: dict[str, Any] = {"apikey": self.api_key}
        else:
            try:
                request_params = dict(params)
            except Exception:
                request_params = {}
            if "apikey" not in request_params:
                request_params["apikey"] = self.api_key

        # For POST, merge overrides from params to data
        post_params = None
        if method.upper() == "POST" and data is not None:
            # Ensure apikey in data
            if "apikey" not in data or not data["apikey"]:
                data["apikey"] = self.api_key
            # Merge domain if in params and missing in data
            if "domain" in request_params and "domain" not in data:
                data["domain"] = request_params["domain"]
            # Send params for overrides (apikey/domain)
            if any(key in request_params for key in ["apikey", "domain"]):
                post_params = request_params

        logger.debug(f"DNS Exit API Request: {method.upper()} {url}")
        logger.debug(
            f"Query Parameters: {self._mask_sensitive_data(request_params if method == 'GET' else post_params)}"
        )
        if data is not None:
            logger.debug(f"Request Body: {self._mask_sensitive_data(self._safe_serialize(data))}")

        start_time = time.time()
        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=request_params, timeout=REQUEST_TIMEOUT)
            elif method.upper() == "POST":
                response = self.session.post(url, params=post_params, json=data, timeout=REQUEST_TIMEOUT)
            else:
                msg = f"Unsupported HTTP method: {method}"
                raise ValueError(msg)

            duration = time.time() - start_time
            status_code = getattr(response, "status_code", "<?>")
            reason = getattr(response, "reason", "")
            logger.info(f"DNS Exit API Response: {status_code} {reason} (Duration: {duration:.2f}s)")

            # Debug headers and brief body info
            headers_keys = list(getattr(response, "headers", {}).keys()) if hasattr(response, "headers") else []
            logger.debug(f"Response Headers keys: {headers_keys}")

            try:
                response_data = response.json()
            except ValueError:
                response_data = None
                text = getattr(response, "text", "")
                if text:
                    logger.debug(f"Response Body length: {len(text)}")

            # Raise for HTTP errors after attempting to parse (to log any message)
            try:
                response.raise_for_status()
            except Exception as e:
                logger.debug(f"Response status check failed: {e}")

            if isinstance(response_data, dict):
                code = response_data.get("code")
                if code is not None and code != 0:
                    logger.warning(f"DNS Exit API Error: {response_data.get('message', 'Unknown error')}")
                logger.debug(f"Response Body code: {response_data.get('code', 'N/A')}")
            return response_data  # may be None

        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            logger.exception(f"DNS Exit API Request Failed: {type(e).__name__}: {e} (Duration: {duration:.2f}s)")
            resp = getattr(e, "response", None)
            if resp is not None:
                try:
                    logger.exception(f"Error Response: {resp.status_code} - {getattr(resp, 'text', '')[:200]}")
                except Exception as read_error:
                    logger.exception(f"Error reading response: {read_error}")
            return None
        except Exception as e:
            duration = time.time() - start_time
            logger.exception(
                f"Unexpected error in DNS Exit API request: {type(e).__name__}: {e} (Duration: {duration:.2f}s)"
            )
            return None

    def add_txt_record(
        self,
        domain: str,
        names: str | list[str],
        values: str | list[str],
        ttl: int = 0,
        overwrite: bool = True,
        params: dict[str, Any] | None = None,
    ) -> bool:
        """
        Add TXT record(s) to a domain (supports single or multiple via lists).

        Args:
            domain: Domain name
            names: Record name(s)
            values: Record value(s) (must match names length)
            ttl: Time to live in minutes (default 0 for LE)
            overwrite: Overwrite if exists
            params: Query overrides (e.g., {'domain': alt_domain})

        Returns:
            True if successful, False otherwise
        """
        if not isinstance(domain, str) or not domain.strip():
            msg = "Invalid domain: must be non-empty string"
            raise ValueError(msg)

        if isinstance(names, str):
            names = [names]
            values = [values] if isinstance(values, str) else values
        if len(names) != len(values):
            msg = "Names and values must have same length"
            raise ValueError(msg)

        actions = []
        for n, v in zip(names, values, strict=False):
            if not isinstance(n, str) or not isinstance(v, str):
                msg = "Names and values must be strings"
                raise ValueError(msg)
            actions.append({"type": "TXT", "name": n, "content": v, "ttl": ttl, "overwrite": overwrite})

        data = {"domain": domain, "add": actions if len(actions) > 1 else actions[0]}

        response = self._make_request("POST", params=params, data=data)
        return bool(response is not None and isinstance(response, dict) and response.get("code") == 0)

    # update_txt_record method removed - use add_txt_record with overwrite=True instead

    def remove_txt_record(self, domain: str, names: str | list[str], params: dict[str, Any] | None = None) -> bool:
        """
        Remove TXT record(s) from a domain (supports single or multiple via list).

        Args:
            domain: Domain name
            names: Record name(s)
            params: Query overrides (e.g., {'domain': alt_domain})
            value: Ignored (for compatibility), not used in API

        Returns:
            True if successful, False otherwise
        """
        if not isinstance(domain, str) or not domain.strip():
            msg = "Invalid domain: must be non-empty string"
            raise ValueError(msg)

        if isinstance(names, str):
            names = [names]
        for n in names:
            if not isinstance(n, str):
                msg = "Names must be strings"
                raise ValueError(msg)

        actions = [{"type": "TXT", "name": n} for n in names]

        data = {"domain": domain, "delete": actions if len(actions) > 1 else actions[0]}

        response = self._make_request("POST", params=params, data=data)
        return bool(response is not None and isinstance(response, dict) and response.get("code") == 0)

    def update_dynamic_ip(self, hosts: str, ip: str | None = None, params: dict[str, Any] | None = None) -> bool:
        """
        Update dynamic IP for hosts via /ud/ endpoint (GET with params).

        Args:
            hosts: Comma-separated hostnames (e.g., 'host1.example.com,host2')
            ip: Optional IP to set (auto-detect if None)
            params: Additional query params

        Returns:
            True if successful, False otherwise
        """
        if not isinstance(hosts, str) or not hosts.strip():
            msg = "Invalid hosts: must be non-empty string"
            raise ValueError(msg)

        ud_url = "https://api.dnsexit.com/dns/ud/"
        p = {"host": hosts} if params is None else dict(params)
        if "host" not in p:
            p["host"] = hosts
        if ip:
            p["ip"] = ip

        response = self._make_request("GET", base_url=ud_url, params=p)
        return bool(response is not None and isinstance(response, dict) and response.get("code") == 0)

    def dns_check_for_txt_record(self, resolver, name: str, value: str) -> bool:
        """
        Check if a TXT record exists with the expected value.

        Args:
            resolver: DNS resolver object
            name: Record name to check (e.g., _acme-challenge.example.com)
            value: Expected TXT record value

        Returns:
            True if record exists with correct value, False otherwise
        """
        import dns.resolver

        try:
            answers = resolver.resolve(name, "TXT")

            # Iterate through all TXT RDATA and their strings
            for rdata in answers:
                # dnspython represents TXT strings as bytes in rdata.strings
                for txt_bytes in getattr(rdata, "strings", []):
                    try:
                        txt_value = txt_bytes.decode("utf-8")
                    except Exception:
                        # Fallback decoding to be robust
                        txt_value = txt_bytes.decode("utf-8", errors="ignore")
                    if txt_value == value:
                        logger.info(f"DNS record found: {name} TXT = '{value}'")
                        return True

            # If reached here, records exist but value didn't match
            try:
                got_values = []
                for rdata in answers:
                    for txt_bytes in getattr(rdata, "strings", []):
                        try:
                            got_values.append(txt_bytes.decode("utf-8"))
                        except Exception:
                            got_values.append(str(txt_bytes))
                logger.debug(f"TXT record exists but value doesn't match. Expected: '{value}', Got: {got_values}")
            except Exception:
                logger.debug("TXT record exists but value doesn't match (unable to render values)")

        except dns.resolver.NXDOMAIN:
            logger.debug(f"DNS record not found yet: {name} (NXDOMAIN)")
        except dns.resolver.NoAnswer:
            logger.debug(f"DNS record not found yet: {name} (NoAnswer)")
        except dns.exception.Timeout:
            logger.debug(f"DNS query timeout for: {name}")
        except Exception as e:
            logger.debug(f"DNS query error for {name}: {e}")

        return False

    def _setup_dns_resolver(self, dns_server: str) -> dns.resolver.Resolver | None:
        """Setup and return configured DNS resolver."""
        import socket

        import dns.resolver

        resolver = dns.resolver.Resolver()

        # Resolve dns_server hostname to IP address if it's not an IP
        try:
            socket.inet_aton(dns_server)  # Raises OSError if not a valid IP
            resolved_nameservers = [dns_server]
        except OSError:
            # Not an IP, try to resolve it as a hostname
            logger.debug(f"Resolving DNS server hostname: {dns_server}")
            try:
                answers = resolver.resolve(dns_server, "A")
                resolved_nameservers = [rdata.address for rdata in answers]
                if not resolved_nameservers:
                    logger.exception(f"Could not resolve DNS server hostname to an IP address: {dns_server}")
                    return None
                logger.info(f"Resolved DNS server '{dns_server}' to IP(s): {resolved_nameservers}")
            except Exception as e:
                logger.exception(f"Failed to resolve DNS server hostname '{dns_server}': {e}")
                return None

        resolver.nameservers = resolved_nameservers
        resolver.timeout = RESOLVER_TIMEOUT
        resolver.lifetime = RESOLVER_TIMEOUT
        return resolver

    def wait_for_propagation(
        self,
        domain: str,
        name: str,
        value: str,
        timeout: int = 300,
        dns_server: str = "ns10.dnsexit.com",
        retry_on_failure: bool = False,
        check_interval: int = 15,
    ) -> bool:
        """
        Wait for DNS record propagation.

        Args:
            domain: Domain name
            name: Record name (e.g., _acme-challenge.example.com)
            value: Record value to check for
            timeout: Maximum time to wait in seconds
            interval: Check interval in seconds (for legacy compatibility, minimum 5 seconds)
            dns_server: DNS server to use for resolution
            retry_on_failure: If True, update record on check failure and retry
            check_interval: Interval between checks when retry_on_failure=True

        Returns:
            True if record propagated, False if timeout
        """
        # Normalize parameters
        try:
            timeout = int(timeout)
        except (TypeError, ValueError):
            logger.exception(f"Invalid timeout value (expected int), got: {timeout!r}")
            return False

        try:
            check_interval = int(check_interval)
        except (TypeError, ValueError):
            logger.exception(f"Invalid check_interval value (expected int), got: {check_interval!r}")
            return False

        # Setup DNS resolver
        resolver = self._setup_dns_resolver(dns_server)
        if resolver is None:
            return False

        logger.info(f"Waiting for DNS propagation: {name} TXT record with value '{value[:20]}...'")
        logger.info(f"DNS server: {dns_server}, Timeout: {timeout}s, Check interval: {check_interval}s")
        if retry_on_failure:
            logger.info("Retry on failure: enabled")

        start_time = time.time()

        while time.time() - start_time < timeout:
            # Check if DNS record has propagated
            if self.dns_check_for_txt_record(resolver, name, value):
                return True

            if retry_on_failure:
                # Record not propagated, update it
                logger.warning("DNS propagation check failed, updating TXT record")
                if not self.add_txt_record(domain, name, value, overwrite=True):
                    logger.error("Failed to update TXT record")
                    return False
                logger.debug("TXT record updated, will recheck after interval")
            # Wait before next check
            elapsed_time = time.time() - start_time
            sleep_time = min(check_interval, max(0, timeout - elapsed_time))
            if sleep_time > 0:
                logger.debug(f"Waiting {sleep_time:.1f}s before next DNS check...")
                time.sleep(sleep_time)

        logger.warning(f"DNS propagation timeout after {timeout}s: {name} TXT record not found")
        return False


if __name__ == "__main__":
    # Simple test
    client = DNSExitClient("test-key")
