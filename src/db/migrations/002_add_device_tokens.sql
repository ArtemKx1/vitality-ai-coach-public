-- Migration 002: Add device_tokens table for push notifications
-- Run with: psql "$DATABASE_URL" -f 002_add_device_tokens.sql

CREATE TABLE IF NOT EXISTS device_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(512) NOT NULL UNIQUE,
    platform VARCHAR(20) NOT NULL DEFAULT 'android',
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- Row-level security: deny all direct data access
ALTER TABLE device_tokens ENABLE ROW LEVEL SECURITY;

-- Only the backend (service_role / superuser) can access this table
-- This policy ensures no one can read/write device_tokens via the Data API
CREATE POLICY "deny_all_device_tokens" ON device_tokens
    FOR ALL
    USING (false)
    WITH CHECK (false);
