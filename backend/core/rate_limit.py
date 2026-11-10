import re
import threading
import time
from collections import defaultdict
from typing import Tuple

from fastapi import HTTPException, Request, status

from backend.core.config import settings


def parse_rate_limit(rate_str: str) -> Tuple[int, int]:
    """
    Parses rate limit string format like '5/minute', '3/minute', '10/second', '100/hour'.
    Returns (max_requests, window_seconds).
    """
    if not rate_str or not isinstance(rate_str, str):
        return 5, 60

    rate_str = rate_str.strip().lower()
    match = re.match(r"^(\d+)\s*/\s*(second|minute|hour|day)$", rate_str)
    if not match:
        try:
            return int(rate_str), 60
        except ValueError:
            return 5, 60

    count = int(match.group(1))
    unit = match.group(2)

    unit_multipliers = {
        "second": 1,
        "minute": 60,
        "hour": 3600,
        "day": 86400
    }
    return count, unit_multipliers.get(unit, 60)


def get_client_ip(request: Request) -> str:
    """
    Safely extracts client IP address from proxy headers or connection info.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # First IP in X-Forwarded-For is the real client IP
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return client_ip

    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


class InMemoryRateLimiter:
    """
    Thread-safe in-memory sliding window rate limiter.
    Does not require external infrastructure (e.g. Redis) for single-instance or local deployment.
    """
    def __init__(self):
        self._records = defaultdict(list)
        self._lock = threading.Lock()

    def is_rate_limited(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
        """
        Records an attempt and checks if the rate limit is exceeded.
        Returns (is_limited, retry_after_seconds).
        """
        now = time.time()
        with self._lock:
            cutoff = now - window_seconds
            # Filter out entries older than current window
            valid_timestamps = [t for t in self._records[key] if t > cutoff]
            self._records[key] = valid_timestamps

            if len(valid_timestamps) >= max_requests:
                oldest_in_window = valid_timestamps[0]
                retry_after = max(1, int(window_seconds - (now - oldest_in_window)))
                return True, retry_after

            # Record this valid attempt
            self._records[key].append(now)
            return False, 0

    def reset(self):
        """Clears all rate limit records (primarily for testing)."""
        with self._lock:
            self._records.clear()


limiter = InMemoryRateLimiter()


def rate_limit_login(request: Request):
    """
    Rate limiting dependency for POST /auth/login.
    Prevents credential brute-forcing while avoiding account enumeration.
    """
    ip = get_client_ip(request)
    max_req, window = parse_rate_limit(settings.LOGIN_RATE_LIMIT)
    limited, retry_after = limiter.is_rate_limited(f"login:{ip}", max_req, window)

    if limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please wait a moment before trying again.",
            headers={"Retry-After": str(retry_after)}
        )


def rate_limit_register(request: Request):
    """
    Rate limiting dependency for POST /auth/register.
    Prevents automated spam registration attacks.
    """
    ip = get_client_ip(request)
    max_req, window = parse_rate_limit(settings.REGISTER_RATE_LIMIT)
    limited, retry_after = limiter.is_rate_limited(f"register:{ip}", max_req, window)

    if limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please wait a moment before trying again.",
            headers={"Retry-After": str(retry_after)}
        )
