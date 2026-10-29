-- Migration: 0001 – Create all tables for QuestPlatform
-- Run with: npx wrangler d1 migrations apply quest-platform-db

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_admin INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    referral_code TEXT NOT NULL UNIQUE,
    referred_by_id INTEGER REFERENCES users(id),
    wallet_balance REAL DEFAULT 0.0,
    referral_earnings REAL DEFAULT 0.0,
    total_earned REAL DEFAULT 0.0,
    tasks_completed_count INTEGER DEFAULT 0,
    bank_name TEXT,
    account_number TEXT,
    account_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code);

CREATE TABLE IF NOT EXISTS access_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    is_used INTEGER DEFAULT 0,
    batch_id TEXT,
    created_by_id INTEGER REFERENCES users(id),
    used_by_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_access_codes_code ON access_codes(code);
CREATE INDEX IF NOT EXISTS idx_access_codes_is_used ON access_codes(is_used);
CREATE INDEX IF NOT EXISTS idx_access_codes_batch_id ON access_codes(batch_id);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT DEFAULT 'Social',
    url TEXT NOT NULL,
    instructions TEXT NOT NULL,
    reward_amount REAL,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tasks_is_active ON tasks(is_active);

CREATE TABLE IF NOT EXISTS task_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES tasks(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    screenshot_path TEXT NOT NULL,
    notes TEXT,
    status TEXT DEFAULT 'pending',
    rejection_reason TEXT,
    reward_paid REAL DEFAULT 0.0,
    reviewed_by_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_task_submissions_status ON task_submissions(status);
CREATE INDEX IF NOT EXISTS idx_task_submissions_created_at ON task_submissions(created_at);

CREATE TABLE IF NOT EXISTS withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    amount REAL NOT NULL,
    bank_name TEXT NOT NULL,
    account_number TEXT NOT NULL,
    account_name TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    admin_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_withdrawals_status ON withdrawals(status);
CREATE INDEX IF NOT EXISTS idx_withdrawals_created_at ON withdrawals(created_at);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    amount REAL NOT NULL,
    tx_type TEXT NOT NULL,
    description TEXT NOT NULL,
    reference_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transactions_tx_type ON transactions(tx_type);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);

CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT
);

-- Seed default system settings
INSERT OR IGNORE INTO system_settings (key, value, description) VALUES
    ('access_code_price', '5000', 'Base access code price X'),
    ('currency_symbol', '₦', 'Platform currency symbol'),
    ('site_name', 'QuestPlatform', 'Brand name'),
    ('allow_any_day_withdrawals', 'false', 'Unlock withdrawals on any day'),
    ('google_ads_enabled', 'false', 'Toggle Google Ads'),
    ('google_ads_client_id', '', 'Google AdSense Publisher ID');
