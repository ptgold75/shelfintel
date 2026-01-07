# ingest/proxy_config.py
"""
Proxy configuration for scraping providers.

Supports CLIproxy.com residential proxies with IP rotation.

Usage:
    Set environment variables:
        PROXY_HOST=unlimit.cliproxy.io
        PROXY_PORT=12345
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

# Pre-generated session IDs for proxy pool (20 Maryland IPs)
PROXY_SESSION_IDS = [
    "VEqKfLHz", "CFNB2W9j", "pK1sCBe2", "jaUsiYvG", "j4kMSe3W",
    "WPLsXHUG", "CCjk3f3m", "3UDkT1qL", "b8KvpwdY", "Nw7bPhgm",
    "5cMrkREc", "3JL3Mcwi", "bKwDMytr", "BEsjzeDU", "gQQjczXG",
    "fqf21GYf", "pYENcTCi", "EmeZc4EW", "FgCYTRmh", "Gn8Ugnie",
]

# Track which session to use next (round-robin)
_session_index = 0


def _get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable."""
    return os.environ.get(key, default)


def get_next_session_id() -> str:
    """Get next session ID from the pool (round-robin)."""
    global _session_index
    session_id = PROXY_SESSION_IDS[_session_index % len(PROXY_SESSION_IDS)]
    _session_index += 1
    return session_id


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
        force_rotate: If True, gets next session ID from pool (or generates new one)
        rotation_minutes: Rotation cycle in minutes (default 5)
        use_pool: If True, use pre-configured session pool; if False, generate random

    Returns:
        Proxy URL like http://user:pass@host:port or None if not configured
    """
    config = get_proxy_config()
    if not config:
        return None

    user = config["user"]

    # CLIproxy rotation: append -sid-xxxx-t-N to username
    # -sid-xxxx = session ID (change to get new IP)
    # -t-N = rotation cycle in minutes
    if force_rotate:
        if use_pool:
            session_id = get_next_session_id()
        else:
            session_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        user = f"{user}-sid-{session_id}-t-{rotation_minutes}"
    else:
        # Use first session from pool for consistent IP within batch
        user = f"{user}-sid-{PROXY_SESSION_IDS[0]}-t-{rotation_minutes}"

    return f"http://{user}:{config['password']}@{config['host']}:{config['port']}"


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
        force_rotate: If True, gets next session ID from pool for new IP
        rotation_minutes: Rotation cycle in minutes (default 5)

    Returns:
        Dict for Playwright proxy config or None if not configured
    """
    config = get_proxy_config()
    if not config:
        return None

    user = config["user"]

    if force_rotate:
        session_id = get_next_session_id()
        user = f"{user}-sid-{session_id}-t-{rotation_minutes}"
    else:
        user = f"{user}-sid-{PROXY_SESSION_IDS[0]}-t-{rotation_minutes}"

    return {
        "server": f"http://{config['host']}:{config['port']}",
        "username": user,
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
