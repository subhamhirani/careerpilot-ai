"""CareerPilot AI — Auth API Router.

Endpoints for user registration, login, token refresh, and TOTP setup.
Uses an in-memory user store (no DB required).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from ..auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_totp_secret,
    get_current_user_id,
    get_totp_uri,
    hash_password,
    refresh_access_token,
    verify_password,
    verify_totp,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# ── In-memory user store ─────────────────────────────────────
_users: dict[str, dict] = {}          # email → {id, email, password_hash}
_email_to_id: dict[str, str] = {}     # email → user_id


def _create_user_in_db(user_id: str, email: str, password_hash: str) -> None:
    """Create a user row in PostgreSQL so FK constraints work for Celery tasks."""
    import os
    from sqlalchemy import create_engine, text

    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        return
    sync_dsn = dsn.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_dsn)
    try:
        with engine.connect() as conn:
            conn.execute(
                text("INSERT INTO users (id, email, hashed_password) VALUES (:id, :email, :pw) ON CONFLICT (id) DO NOTHING"),
                {"id": user_id, "email": email, "pw": password_hash},
            )
            conn.commit()
    finally:
        engine.dispose()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str | None = None
    role: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register", status_code=201)
async def register(body: RegisterRequest):
    """Register a new user with email + password."""
    if body.email in _email_to_id:
        raise HTTPException(status_code=409, detail="Email already registered")

    user_id = str(uuid.uuid4())
    _users[user_id] = {
        "id": user_id,
        "email": body.email,
        "password_hash": hash_password(body.password),
    }
    _email_to_id[body.email] = user_id

    # Also create user in the database so FK constraints work
    try:
        _create_user_in_db(user_id, body.email, _users[user_id]["password_hash"])
    except Exception as db_err:
        import logging
        logging.getLogger(__name__).warning("Failed to create user in DB: %s", db_err)

    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)

    return {
        "user_id": user_id,
        "email": body.email,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/login")
async def login(body: LoginRequest):
    """Authenticate and issue JWT tokens."""
    user_id = _email_to_id.get(body.email)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user = _users[user_id]
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh")
async def refresh(refresh_token: str):
    """Exchange a refresh token for a new token pair."""
    try:
        return refresh_access_token(refresh_token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=str(exc))


@router.get("/me")
async def get_me(user_id: str = Depends(get_current_user_id)):
    """Return the current authenticated user's ID."""
    user = _users.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user_id, "email": user["email"]}


@router.post("/totp/setup")
async def setup_totp(user_id: str = Depends(get_current_user_id)):
    """Generate a new TOTP secret and provisioning URI."""
    secret = generate_totp_secret()
    email = _users[user_id]["email"]
    uri = get_totp_uri(secret, email)
    return {"secret": secret, "uri": uri}


@router.post("/totp/verify")
async def verify_totp_endpoint(
    secret: str,
    token: str,
    user_id: str = Depends(get_current_user_id),
):
    """Verify a TOTP token against the provided secret."""
    valid = verify_totp(secret, token)
    return {"valid": valid}
