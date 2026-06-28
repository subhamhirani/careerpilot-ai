-- Migration 004: Password reset tokens table
-- Generates cryptographically secure reset tokens stored as SHA-256 hashes

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(64) NOT NULL,       -- SHA-256 hex of the raw token
    expires_at  TIMESTAMPTZ NOT NULL,
    used        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reset_tokens_user_id ON password_reset_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_reset_tokens_expires ON password_reset_tokens(expires_at)
    WHERE used = FALSE;
