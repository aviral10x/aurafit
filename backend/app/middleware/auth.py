"""
Supabase JWT auth middleware.
Validates the Authorization: Bearer <token> header issued by Supabase Auth.
"""
from __future__ import annotations

from typing import Optional

from fastapi import Header, HTTPException
from jose import JWTError, jwt

from app.config import settings


def get_optional_user(authorization: Optional[str] = Header(default=None)) -> Optional[dict]:
    """
    Extract user info from Supabase JWT if present.
    Returns None if no token — allows unauthenticated access.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    return _decode_token(token)


def get_required_user(authorization: Optional[str] = Header(default=None)) -> dict:
    """
    Same as get_optional_user but raises 401 if not authenticated.
    """
    user = get_optional_user(authorization)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user


def _decode_token(token: str) -> Optional[dict]:
    if not settings.supabase_jwt_secret:
        return None  # Auth disabled in mock mode
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return {
            "id": payload.get("sub"),
            "email": payload.get("email"),
            "role": payload.get("role", "authenticated"),
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired session. Please log in again.")
