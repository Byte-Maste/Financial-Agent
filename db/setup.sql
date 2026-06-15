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

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================
-- Tables
-- =============================================================

-- 1. Users
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    current_balance DECIMAL(12,2) NOT NULL DEFAULT 0,
    monthly_income DECIMAL(12,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Transactions
CREATE TABLE transactions (
    transaction_id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    date DATE NOT NULL,
    amount DECIMAL(12,2) NOT NULL CHECK (amount > 0),
    merchant TEXT NOT NULL,
    raw_merchant TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'Uncategorized',
    payment_mode TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_date ON transactions(date);
CREATE INDEX idx_transactions_category ON transactions(category);

-- 3. Merchant embeddings (pgvector)
--    voyage-3-lite produces 512-dimensional vectors
CREATE TABLE merchant_embeddings (
    merchant_name TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    embedding VECTOR(512) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================
-- Seed data
-- =============================================================

INSERT INTO users (current_balance, monthly_income)
VALUES (50000, 75000);

-- Print the generated UUID for reference
SELECT user_id AS test_user_id FROM users LIMIT 1;
