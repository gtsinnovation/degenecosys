-- backend/database/schema.sql
-- PostgreSQL bootstrap schema kept in sync with backend/app/schema.prisma.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE warriors (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    wallet_address TEXT NOT NULL UNIQUE,
    username TEXT UNIQUE,
    avatar_url TEXT,
    bio TEXT,
    banner_url TEXT,
    twitter_handle TEXT,
    created_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE warrior_xp (
    warrior_id TEXT PRIMARY KEY REFERENCES warriors(id) ON DELETE CASCADE,
    current_xp INTEGER NOT NULL DEFAULT 0,
    rank_tier INTEGER NOT NULL DEFAULT 1,
    updated_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE community_upvotes (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    voter_id TEXT NOT NULL REFERENCES warriors(id) ON DELETE CASCADE,
    target_id TEXT NOT NULL REFERENCES warriors(id) ON DELETE CASCADE,
    weight DOUBLE PRECISION NOT NULL DEFAULT 1.00,
    created_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT community_upvotes_voter_id_target_id_key UNIQUE (voter_id, target_id)
);

CREATE TABLE wallet_balance_snapshots (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    wallet_address TEXT NOT NULL,
    token_balance DOUBLE PRECISION NOT NULL,
    circulating_percentage DOUBLE PRECISION NOT NULL,
    snapshot_date TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT wallet_balance_snapshots_wallet_address_snapshot_date_key UNIQUE (wallet_address, snapshot_date)
);

CREATE TABLE contests (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    title TEXT NOT NULL,
    description TEXT,
    prize_pool_dd DOUBLE PRECISION NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    start_date TIMESTAMP(3) NOT NULL,
    end_date TIMESTAMP(3) NOT NULL,
    created_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE contest_submissions (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    contest_id TEXT NOT NULL REFERENCES contests(id) ON DELETE CASCADE,
    warrior_id TEXT NOT NULL REFERENCES warriors(id) ON DELETE CASCADE,
    submission_link TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    reward_paid BOOLEAN NOT NULL DEFAULT FALSE,
    xp_awarded BOOLEAN NOT NULL DEFAULT FALSE,
    tx_signature TEXT,
    created_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE badges (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    icon_svg TEXT NOT NULL,
    xp_requirement_threshold INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE warrior_earned_badges (
    warrior_id TEXT NOT NULL REFERENCES warriors(id) ON DELETE CASCADE,
    badge_id TEXT NOT NULL REFERENCES badges(id) ON DELETE CASCADE,
    unlocked_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT warrior_earned_badges_pkey PRIMARY KEY (warrior_id, badge_id)
);

CREATE TABLE wallet_challenges (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    wallet_address TEXT NOT NULL,
    nonce TEXT NOT NULL UNIQUE,
    message TEXT NOT NULL,
    expires_at TIMESTAMP(3) NOT NULL,
    used_at TIMESTAMP(3),
    created_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_xp_leaderboard ON warrior_xp(current_xp DESC);
CREATE INDEX idx_snapshots_lookup ON wallet_balance_snapshots(wallet_address, snapshot_date);
CREATE INDEX idx_upvotes_target ON community_upvotes(target_id);
CREATE INDEX idx_wallet_challenges_wallet_expires ON wallet_challenges(wallet_address, expires_at);

-- Keep updated_at values current for direct SQL updates as well as Prisma writes.
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_warriors_modtime
    BEFORE UPDATE ON warriors FOR EACH ROW EXECUTE FUNCTION update_modified_column();
CREATE TRIGGER update_xp_modtime
    BEFORE UPDATE ON warrior_xp FOR EACH ROW EXECUTE FUNCTION update_modified_column();
