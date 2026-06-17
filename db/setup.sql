-- =============================================================
-- Autonomous Financial Wellness Agent — Local DB Setup
-- =============================================================
-- Usage:
--   1. Ensure PostgreSQL 16+ is running on localhost:5432
--   2. psql -U postgres -f db/setup.sql
-- =============================================================

-- Drop database if re-running setup
DROP DATABASE IF EXISTS financial_agent;

-- Create database
CREATE DATABASE financial_agent;

-- Connect to it
\c financial_agent

-- =============================================================
-- Tables
-- =============================================================

-- 1. Users
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    current_balance DECIMAL(12,2) NOT NULL DEFAULT 0,
    monthly_income DECIMAL(12,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Transactions
CREATE TABLE transactions (
    transaction_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    date DATE NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    transaction_type TEXT NOT NULL DEFAULT 'debit',
    merchant TEXT NOT NULL,
    raw_merchant TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'Uncategorized',
    payment_mode TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_date ON transactions(date);
CREATE INDEX idx_transactions_category ON transactions(category);

-- 3. Merchant embeddings (JSONB — no pgvector dependency)
--    voyage-3-lite produces 512-dimensional vectors
CREATE TABLE merchant_embeddings (
    merchant_name TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    embedding JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5. Financial Goals
CREATE TABLE goals (
    goal_id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    target_amount DECIMAL(12,2) NOT NULL,
    target_date DATE NOT NULL,
    current_progress DECIMAL(12,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_goals_user_id ON goals(user_id);

-- 6. Alerts
CREATE TABLE alerts (
    alert_id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_alerts_user_id ON alerts(user_id);
CREATE INDEX idx_alerts_created_at ON alerts(created_at);

-- =============================================================
-- Seed data
-- =============================================================

INSERT INTO users (user_id, current_balance, monthly_income)
VALUES ('4616', 50000, 75000);
