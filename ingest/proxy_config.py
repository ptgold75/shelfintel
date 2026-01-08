# ingest/proxy_config.py
"""
Proxy configuration for scraping providers.

Supports Decodo residential proxies with sticky sessions.

Usage:
    Set environment variables:
        PROXY_HOST=gate.decodo.com
        PROXY_PORT=10001
        PROXY_USER=your_username
        PROXY_PASS=your_password

    Or use .env file in project root.
"""

import os
import random
import string
from typing import Optional, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Track which port to use for rotation (Decodo provides ports 10001-10010)
_port_index = 0
DECODO_PORTS = [10001, 10002, 10003, 10004, 10005, 10006, 10007, 10008, 10009, 10010]


def _get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable."""
    return os.environ.get(key, default)


def get_next_port() -> int:
    """Get next port from the pool (round-robin) for IP rotation."""
    global _port_index
    port = DECODO_PORTS[_port_index % len(DECODO_PORTS)]
    _port_index += 1
    return port


def get_proxy_config() -> Optional[Dict[str, str]]:
    """
    Get proxy configuration from environment variables.

    Returns:
        Dict with proxy settings or None if not configured
    """
    host = _get_env("PROXY_HOST")
    port = _get_env("PROXY_PORT")
    user = _get_env("PROXY_USER")
    password = _get_env("PROXY_PASS")

    if not all([host, port, user, password]):
        return None

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
    }


def get_proxy_url(force_rotate: bool = False, rotation_minutes: int = 5, use_pool: bool = True) -> Optional[str]:
    """
    Get HTTP proxy URL for requests library.

    Args:
        force_rotate: If True, uses next port for IP rotation
        rotation_minutes: Not used for Decodo (sessions are sticky by default)
        use_pool: Not used for Decodo

    Returns:
        Proxy URL like http://user:pass@host:port or None if not configured
    """
    config = get_proxy_config()
    if not config:
        return None

    user = config["user"]
    password = config["password"]
    host = config["host"]

    # Decodo: use different ports for IP rotation
    # Each port gives a different sticky IP
    if force_rotate:
        port = get_next_port()
    else:
        port = int(config["port"])

    return f"http://{user}:{password}@{host}:{port}"


def get_proxies_dict(force_rotate: bool = False) -> Optional[Dict[str, str]]:
    """
    Get proxies dict for requests library.

    Args:
        force_rotate: If True, generates a new session ID to force IP rotation

    Returns:
        Dict like {"http": "...", "https": "..."} or None if not configured
    """
    proxy_url = get_proxy_url(force_rotate=force_rotate)
    if not proxy_url:
        return None

    return {
        "http": proxy_url,
        "https": proxy_url,
    }


def get_playwright_proxy(force_rotate: bool = False, rotation_minutes: int = 5) -> Optional[Dict[str, str]]:
    """
    Get proxy config for Playwright browser.

    Args:
        force_rotate: If True, uses next port for new IP
        rotation_minutes: Not used for Decodo

    Returns:
        Dict for Playwright proxy config or None if not configured
    """
    config = get_proxy_config()
    if not config:
        return None

    # Decodo: use different ports for IP rotation
    if force_rotate:
        port = get_next_port()
    else:
        port = int(config["port"])

    return {
        "server": f"http://{config['host']}:{port}",
        "username": config["user"],
        "password": config["password"],
    }


# Rate limiting helpers
class RateLimiter:
    """Simple rate limiter for API requests."""

    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute
        self.last_request_time = 0.0

    def wait(self):
        """Wait if necessary to respect rate limit."""
        import time
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()


# Default rate limiters per provider
RATE_LIMITERS = {
    "sweed": RateLimiter(requests_per_minute=60),
    "dutchie": RateLimiter(requests_per_minute=30),
    "jane": RateLimiter(requests_per_minute=30),
}


def get_rate_limiter(provider: str) -> RateLimiter:
    """Get rate limiter for a specific provider."""
    return RATE_LIMITERS.get(provider, RateLimiter(requests_per_minute=30))
