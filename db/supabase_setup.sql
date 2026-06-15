-- =============================================================
-- Autonomous Financial Wellness Agent - Database Schema
-- Run this in Supabase SQL Editor or local PostgreSQL
-- =============================================================
-- Prerequisites:
--   - pgvector extension: CREATE EXTENSION IF NOT EXISTS vector;
--   - For Supabase: pgvector is pre-installed
-- =============================================================

-- 1. Users table
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    current_balance DECIMAL(12,2) NOT NULL DEFAULT 0,
    monthly_income DECIMAL(12,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Transactions table
CREATE TABLE transactions (
    transaction_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
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

-- 4. Seed a test user
INSERT INTO users (user_id, current_balance, monthly_income)
VALUES ('4616', 50000, 75000);
