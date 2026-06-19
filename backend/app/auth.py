"""CareerPilot AI — JWT Authentication, Password Hashing & TOTP 2FA.

Provides:
- Password hashing with bcrypt (direct, not via passlib)
- Access tokens (15 min default) and refresh tokens (7 days)
- TOTP two-factor authentication support
- Dependency-injection helpers for FastAPI routes
"""

from __future__ import annotations

import bcrypt
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

# Load .env so os.getenv works even if main.py hasn't imported us yet
load_dotenv()

# ──────────────────────────────────────────────
#  Configuration
# ──────────────────────────────────────────────

SECRET_KEY: str = os.getenv("SECRET_KEY", "insecure-dev-secret")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15")
)
REFRESH_TOKEN_EXPIRE_DAYS: int = int(
    os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")
)
TOTP_ISSUER_NAME: str = os.getenv("TOTP_ISSUER_NAME", "CareerPilot AI")

# ──────────────────────────────────────────────
#  Password hashing (direct bcrypt, no passlib)
# ──────────────────────────────────────────────


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    rounds = 4 if os.getenv("ENV", "development") != "production" else 12
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=rounds)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return ``True`` if *plain* matches the bcrypt *hashed* value."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ──────────────────────────────────────────────
#  TOTP 2FA
# ──────────────────────────────────────────────

try:
    import pyotp

    def generate_totp_secret() -> str:
        """Generate a new base32 TOTP secret."""
        return pyotp.random_base32()

    def get_totp_uri(secret: str, email: str) -> str:
        """Build an otpauth:// URI for QR-code enrolment."""
        return pyotp.totp.TOTP(secret).provisioning_uri(
            name=email, issuer_name=TOTP_ISSUER_NAME
        )

    def verify_totp(secret: str, token: str) -> bool:
        """Validate a 6-digit TOTP token against *secret*."""
        return pyotp.TOTP(secret).verify(token)

except ImportError:
    # Fallback when pyotp is not installed (CI / dev)
    import warnings
    warnings.warn("pyotp not installed; TOTP functions are stubbed out.")

    def generate_totp_secret() -> str:
        return "MOCK" + uuid.uuid4().hex[:24].upper()

    def get_totp_uri(secret: str, email: str) -> str:
        return f"otpauth://totp/{TOTP_ISSUER_NAME}:{email}?secret={secret}&issuer={TOTP_ISSUER_NAME}"

    def verify_totp(secret: str, token: str) -> bool:
        # Always accept "000000" in mock mode to ease dev
        return token == "000000"


# ──────────────────────────────────────────────
#  JWT token helpers
# ──────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    subject: str,
    extra_claims: Optional[dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Issue a short-lived JWT access token.

    Args:
        subject: Usually the user ID (UUID as string).
        extra_claims: Optional additional claims to embed.
        expires_delta: Custom expiry; defaults to ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        Encoded JWT string.
    """
    expire = _now() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": _now(),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """Issue a long-lived refresh token (default 7 days).

    Args:
        subject: Usually the user ID (UUID as string).

    Returns:
        Encoded JWT string.
    """
    expire = _now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": _now(),
        "type": "refresh",
        # Unique jti so a single refresh token can be revoked individually
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.

    Raises:
        HTTPException (401) if the token is expired or invalid.

    Returns:
        The decoded payload dict.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token, SECRET_KEY, algorithms=[JWT_ALGORITHM]
        )
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def refresh_access_token(refresh_token: str) -> dict[str, str]:
    """Exchange a valid refresh token for a new access+refresh pair.

    Args:
        refresh_token: The existing refresh token.

    Returns:
        Dict with ``access_token``, ``refresh_token``, and ``token_type``.
    """
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not a refresh token",
        )
    subject: str = payload["sub"]
    return {
        "access_token": create_access_token(subject),
        "refresh_token": create_refresh_token(subject),
        "token_type": "bearer",
    }


# ──────────────────────────────────────────────
#  FastAPI dependency (Bearer token)
# ──────────────────────────────────────────────

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> str:
    """FastAPI dependency — extract and validate the current user ID from the
    Bearer token.

    Returns:
        User UUID as a string.

    Raises:
        HTTPException 401 if no token or token invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not an access token",
        )
    return payload["sub"]
