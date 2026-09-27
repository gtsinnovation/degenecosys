-- backend/database/schema.sqlsql-- Degen Ecosystem Database Initialization Schema
-- Target Database Engine: PostgreSQL 15+

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. WARRIOR PROFILES TABLE
-- Stores authenticated identity records linked directly to on-chain Solana public keys.
CREATE TABLE warriors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_address VARCHAR(44) UNIQUE NOT NULL, -- Solana base58 wallet address length
    username VARCHAR(50) UNIQUE,
    avatar_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. LIVE XP SYSTEM TRACKING TABLE
-- Keeps current gamified score. Enforces strict constraints matching the roadmap (+100 max, -100 min).
CREATE TABLE warrior_xp (
    warrior_id UUID PRIMARY KEY REFERENCES warriors(id) ON DELETE CASCADE,
    current_xp INT NOT NULL DEFAULT 0,
    rank_tier INT NOT NULL DEFAULT 1, -- Unlocks reward multipliers at different tiers
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT check_xp_range CHECK (current_xp >= -100 AND current_xp <= 100)
);

-- 3. UPVOTE HISTORIES TABLE
-- Records upvotes between ecosystem members. A composite unique key prevents duplicate voting actions.
CREATE TABLE community_upvotes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    voter_id UUID NOT NULL REFERENCES warriors(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES warriors(id) ON DELETE CASCADE,
    weight NUMERIC(5,2) NOT NULL DEFAULT 1.00, -- Weighted if the voter has whale booster status
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_voter_target UNIQUE (voter_id, target_id),
    CONSTRAINT prevent_self_vote CHECK (voter_id <> target_id)
);

-- 4. HISTORICAL WHALE SNAPSHOT DATA TABLE
-- Tracks historical wallet balances over time to programmatically verify the 30-day 2% holding rule.
CREATE TABLE wallet_balance_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_address VARCHAR(44) NOT NULL,
    token_balance NUMERIC(28, 9) NOT NULL, -- Supports 1B max supply + 9 decimal places
    circulating_percentage NUMERIC(5, 2) NOT NULL, -- Pre-calculated percentage share
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    
    CONSTRAINT unique_wallet_per_day UNIQUE (wallet_address, snapshot_date)
);

-- 5. CONTESTS & CHALLENGES RECORDS TABLE
-- Manages administrative parameters for active community challenges.
CREATE TABLE contests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    prize_pool_dd NUMERIC(28, 9) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. CONTEST SUBMISSIONS & OUTCOMES TABLE
-- Documents which warriors participated in contests and tracks verification status.
CREATE TABLE contest_submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contest_id UUID NOT NULL REFERENCES contests(id) ON DELETE CASCADE,
    warrior_id UUID NOT NULL REFERENCES warriors(id) ON DELETE CASCADE,
    submission_link TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- PENDING, APPROVED, REJECTED, WINNER
    reward_paid BOOLEAN NOT NULL DEFAULT FALSE,
    tx_signature VARCHAR(88), -- On-chain transaction reference hash
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- PERFORMANCE INDEX OPTIMIZATIONS
-- ==========================================

-- Speeds up leaderboard lookups by matching addresses instantly
CREATE INDEX idx_warriors_wallet ON warriors(wallet_address);

-- Speeds up the leaderboard sorting algorithm by placing highest XP warriors at the top
CREATE INDEX idx_xp_leaderboard ON warrior_xp(current_xp DESC);

-- Optimizes the background verification scan looking back 30 days for continuous whale holdings
CREATE INDEX idx_snapshots_lookup ON wallet_balance_snapshots(wallet_address, snapshot_date);

-- Tracks total upvotes targeted to a specific warrior efficiently
CREATE INDEX idx_upvotes_target ON community_upvotes(target_id);

-- ==========================================
-- AUTOMATIC TIMESTAMPS TRIGGER FUNCTION
-- ==========================================
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_warriors_modtime BEFORE UPDATE ON warriors FOR EACH ROW EXECUTE FUNCTION update_modified_column();
CREATE TRIGGER update_xp_modtime BEFORE UPDATE ON warrior_xp FOR EACH ROW EXECUTE FUNCTION update_modified_column();
