"""
Simple in-memory sliding-window rate limiter.
For production with multiple workers, swap for Redis/Upstash.
"""
from __future__ import annotations

import time
from collections import defaultdict
from fastapi import HTTPException, Request


# { ip: [timestamp, ...] }
_ip_windows: dict[str, list[float]] = defaultdict(list)
# { email: [timestamp, ...] }
_email_windows: dict[str, list[float]] = defaultdict(list)

WINDOW = 86400  # 24 hours in seconds


def _prune(timestamps: list[float], window: int) -> list[float]:
    now = time.time()
    return [t for t in timestamps if now - t < window]


def check_ip_limit(request: Request, limit: int = 5) -> str:
    """Raise 429 if the IP has exceeded its daily analysis limit."""
    ip = request.client.host if request.client else "unknown"
    _ip_windows[ip] = _prune(_ip_windows[ip], WINDOW)
    if len(_ip_windows[ip]) >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily limit of {limit} analyses per IP reached. Try again tomorrow.",
        )
    _ip_windows[ip].append(time.time())
    return ip


def check_email_limit(email: str, limit: int = 3) -> None:
    """Raise 429 if the authenticated user has exceeded their daily analysis limit."""
    _email_windows[email] = _prune(_email_windows[email], WINDOW)
    if len(_email_windows[email]) >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily limit of {limit} analyses per account reached. Try again tomorrow.",
        )
    _email_windows[email].append(time.time())


def check_otp_rate(email: str, limit: int = 3, window: int = 60) -> None:
    """Prevent OTP spam: max 3 requests per email per minute."""
    key = f"otp:{email}"
    _ip_windows[key] = _prune(_ip_windows[key], window)
    if len(_ip_windows[key]) >= limit:
        raise HTTPException(
            status_code=429,
            detail="Too many OTP requests. Please wait 60 seconds.",
        )
    _ip_windows[key].append(time.time())
