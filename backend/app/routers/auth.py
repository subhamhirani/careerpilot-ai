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
    generate_reset_token,
    generate_totp_secret,
    get_current_user_id,
    get_reset_token_expiry,
    get_totp_uri,
    hash_password,
    hash_reset_token,
    refresh_access_token,
    verify_password,
    verify_totp,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# ── In-memory user store ─────────────────────────────────────
_users: dict[str, dict] = {}          # email → {id, email, password_hash}
_email_to_id: dict[str, str] = {}     # email → user_id


def _create_user_in_db(user_id: str, email: str, password_hash: str) -> str:
    """Create a user row in PostgreSQL so FK constraints work for Celery tasks.
    Returns the actual user_id (may differ from input if email already existed).
    """
    import os
    from sqlalchemy import create_engine, text

    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        return user_id
    sync_dsn = dsn.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_dsn)
    try:
        with engine.connect() as conn:
            # Try insert first
            result = conn.execute(
                text("INSERT INTO users (id, email, hashed_password) VALUES (:id, :email, :pw) ON CONFLICT (email) DO NOTHING RETURNING id"),
                {"id": user_id, "email": email, "pw": password_hash},
            )
            row = result.fetchone()
            if row:
                conn.commit()
                return user_id
            # Conflict: user already exists, fetch existing user_id
            existing = conn.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": email},
            ).fetchone()
            conn.commit()
            return str(existing[0]) if existing else user_id
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


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    """Request a password reset. Returns the reset token in the response.

    In a production environment this token would be sent via email.
    For development it is returned directly.
    """
    import os

    from sqlalchemy import create_engine, text

    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        raise HTTPException(status_code=500, detail="Database not configured")
    sync_dsn = dsn.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_dsn)

    try:
        with engine.connect() as conn:
            # Find user by email
            user = conn.execute(
                text("SELECT id FROM users WHERE email = :email AND is_active = TRUE"),
                {"email": body.email},
            ).fetchone()

            if not user:
                # Return success even for unknown emails to prevent email enumeration
                return {
                    "message": "If an account with that email exists, a reset token has been generated.",
                    "token": None,
                }

            user_id = user[0]

            # Invalidate any existing unused tokens for this user
            conn.execute(
                text(
                    "UPDATE password_reset_tokens SET used = TRUE "
                    "WHERE user_id = :uid AND used = FALSE"
                ),
                {"uid": user_id},
            )

            # Generate new token
            raw_token, token_hash = generate_reset_token()
            expires_at = get_reset_token_expiry()

            conn.execute(
                text(
                    "INSERT INTO password_reset_tokens (user_id, token_hash, expires_at) "
                    "VALUES (:uid, :hash, :exp)"
                ),
                {"uid": user_id, "hash": token_hash, "exp": expires_at},
            )
            conn.commit()

            return {
                "message": "If an account with that email exists, a reset token has been generated.",
                "token": raw_token,
            }
    finally:
        engine.dispose()


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    """Reset a user's password using a valid reset token."""
    import os

    from sqlalchemy import create_engine, text

    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        raise HTTPException(status_code=500, detail="Database not configured")
    sync_dsn = dsn.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_dsn)

    token_hash = hash_reset_token(body.token)

    try:
        with engine.connect() as conn:
            # Find valid token
            row = conn.execute(
                text(
                    "SELECT id, user_id, expires_at FROM password_reset_tokens "
                    "WHERE token_hash = :hash AND used = FALSE AND expires_at > NOW()"
                ),
                {"hash": token_hash},
            ).fetchone()

            if not row:
                raise HTTPException(
                    status_code=400, detail="Invalid or expired reset token"
                )

            token_id = row[0]
            user_id = row[1]

            # Update the password
            new_hash = hash_password(body.new_password)
            conn.execute(
                text("UPDATE users SET hashed_password = :pw, updated_at = NOW() WHERE id = :uid"),
                {"pw": new_hash, "uid": user_id},
            )

            # Mark token as used
            conn.execute(
                text("UPDATE password_reset_tokens SET used = TRUE WHERE id = :tid"),
                {"tid": token_id},
            )

            conn.commit()

            # Update in-memory store so the new password works immediately
            if user_id in _users:
                _users[user_id]["password_hash"] = new_hash

            return {"message": "Password has been reset successfully."}
    finally:
        engine.dispose()


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
    db_err = None
    try:
        actual_user_id = _create_user_in_db(user_id, body.email, _users[user_id]["password_hash"])
    except Exception as e:
        db_err = e
        actual_user_id = None
        import logging
        logging.getLogger(__name__).error("Failed to create user in DB: %s", e)

    if db_err is not None:
        # Roll back in-memory user so we don't have an inconsistent state
        del _users[user_id]
        del _email_to_id[body.email]
        raise HTTPException(status_code=500, detail="Failed to create user in database. Please try again.")

    # If the email already existed in DB, use the existing user_id
    # and preserve the in-memory mapping with the correct ID/password
    if actual_user_id and actual_user_id != user_id:
        saved_hash = _users[user_id]["password_hash"]
        del _users[user_id]
        # Also update the DB so all workers see the new password hash
        import os as _os
        sync_dsn = _os.getenv("DATABASE_URL", "").replace("+asyncpg", "+psycopg2")
        if sync_dsn:
            from sqlalchemy import create_engine as _c, text as _t
            _engine = _c(sync_dsn)
            try:
                with _engine.connect() as _conn:
                    _conn.execute(
                        _t("UPDATE users SET hashed_password = :pw, updated_at = NOW() WHERE id = :uid"),
                        {"pw": saved_hash, "uid": actual_user_id},
                    )
                    _conn.commit()
            finally:
                _engine.dispose()
        user_id = actual_user_id
        _users[user_id] = {"id": user_id, "email": body.email, "password_hash": saved_hash}
        _email_to_id[body.email] = user_id

    access_token = create_access_token(str(user_id))
    refresh_token = create_refresh_token(str(user_id))

    return {
        "user_id": user_id,
        "email": body.email,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


def _verify_login_db(email: str, password: str) -> str:
    """Look up user by email in DB, verify password, populate in-memory cache.
    Returns user_id (UUID string) on success, raises HTTPException(401) on failure."""
    import os
    from sqlalchemy import create_engine, text
    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    sync_dsn = dsn.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_dsn)
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT id, hashed_password FROM users WHERE email = :email"),
                {"email": email},
            ).fetchone()
            if result is None:
                raise HTTPException(status_code=401, detail="Invalid email or password")
            user_id = str(result[0])
            db_hash = result[1]
        if not verify_password(password, db_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        # Re-populate in-memory store for subsequent requests
        _users[user_id] = {"id": user_id, "email": email, "password_hash": db_hash}
        _email_to_id[email] = user_id
        return user_id
    finally:
        engine.dispose()


@router.post("/login")
async def login(body: LoginRequest):
    """Authenticate and issue JWT tokens. Checks in-memory store first, then DB."""
    user_id = _email_to_id.get(body.email)

    if user_id is not None:
        # In-memory user found - check the cached hash
        user = _users[user_id]
        if not verify_password(body.password, user["password_hash"]):
            # In-memory hash may be stale (password was reset by a different worker).
            # Fall through to the DB path for the canonical check.
            user_id = _verify_login_db(body.email, body.password)
        else:
            # In-memory hash matched — but it might be stale on another worker.
            # Verify the DB hasn't moved on (e.g. password reset hit a different worker).
            import os
            from sqlalchemy import create_engine, text
            dsn = os.getenv("DATABASE_URL", "")
            if dsn:
                sync_dsn = dsn.replace("+asyncpg", "+psycopg2")
                engine = create_engine(sync_dsn)
                try:
                    with engine.connect() as conn:
                        result = conn.execute(
                            text("SELECT hashed_password FROM users WHERE id = :uid"),
                            {"uid": user_id},
                        ).fetchone()
                        if result is not None and result[0] != user["password_hash"]:
                            # Password was rotated — in-memory hash is stale.
                            # Update cached hash and re-verify.
                            db_hash = result[0]
                            if not verify_password(body.password, db_hash):
                                raise HTTPException(status_code=401, detail="Invalid email or password")
                            _users[user_id]["password_hash"] = db_hash
                finally:
                    engine.dispose()
    else:
        # Fall back to database check
        user_id = _verify_login_db(body.email, body.password)

    access_token = create_access_token(str(user_id))
    refresh_token = create_refresh_token(str(user_id))

    # Determine if this is a first-time login (no profile, no resumes)
    is_new_user = True
    try:
        import os
        from sqlalchemy import create_engine, text as _text
        dsn = os.getenv("DATABASE_URL", "")
        if dsn:
            sync_dsn = dsn.replace("+asyncpg", "+psycopg2")
            chk_engine = create_engine(sync_dsn)
            try:
                with chk_engine.connect() as conn:
                    prof = conn.execute(
                        _text("SELECT 1 FROM user_profiles WHERE user_id = :uid"),
                        {"uid": user_id},
                    ).fetchone()
                    if prof:
                        is_new_user = False
            finally:
                chk_engine.dispose()
    except Exception:
        pass

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "is_new_user": is_new_user,
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
        # Look up from DB
        import os
        from sqlalchemy import create_engine, text
        dsn = os.getenv("DATABASE_URL", "")
        if dsn:
            sync_dsn = dsn.replace("+asyncpg", "+psycopg2")
            engine = create_engine(sync_dsn)
            try:
                with engine.connect() as conn:
                    result = conn.execute(
                        text("SELECT email FROM users WHERE id = :id"),
                        {"id": user_id},
                    ).fetchone()
                    if result:
                        return {"user_id": user_id, "email": result[0]}
            finally:
                engine.dispose()
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
