-- SQL script to create referral state manager tables
-- Database: referrral_intel
-- Schema: public
--
-- This script creates:
--   1. referral_state_manager - Main referral records table
--   2. referral_state_history - State transition audit trail
--
-- ⚠️ SAFE TO RUN: This only creates NEW tables, does not modify existing ones

-- ============================================================================
-- Table: referral_state_manager
-- ============================================================================
-- Main table for storing referral records with their current state and mermaid diagrams

CREATE TABLE IF NOT EXISTS referral_state_manager (
    referral_id VARCHAR(255) PRIMARY KEY NOT NULL,
    state VARCHAR(50) NOT NULL,
    attributes JSONB DEFAULT '{}'::jsonb,
    mermaid_script TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,  -- Note: Python attribute is 'meta_data' to avoid SQLAlchemy conflict
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_by VARCHAR(255)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_referral_state_manager_referral_id 
    ON referral_state_manager(referral_id);
CREATE INDEX IF NOT EXISTS idx_referral_state_manager_state 
    ON referral_state_manager(state);
CREATE INDEX IF NOT EXISTS idx_referral_state_manager_created_at 
    ON referral_state_manager(created_at);

-- Add comment to table
COMMENT ON TABLE referral_state_manager IS 
    'Main table for storing referral records with their current state and mermaid diagrams';

COMMENT ON COLUMN referral_state_manager.referral_id IS 
    'Primary key: Unique identifier for each referral';
COMMENT ON COLUMN referral_state_manager.state IS 
    'Current state of the referral (referral_received, completed, needs_review, incomplete, rejected)';
COMMENT ON COLUMN referral_state_manager.attributes IS 
    'Flexible JSONB field storing all referral attributes/data';
COMMENT ON COLUMN referral_state_manager.mermaid_script IS 
    'Mermaid diagram script for frontend visualization';
COMMENT ON COLUMN referral_state_manager.metadata IS 
    'Additional metadata in JSONB format (e.g., diagram version, generation timestamp)';
COMMENT ON COLUMN referral_state_manager.created_at IS 
    'Timestamp when the referral record was created';
COMMENT ON COLUMN referral_state_manager.updated_at IS 
    'Timestamp when the referral record was last updated';
COMMENT ON COLUMN referral_state_manager.created_by IS 
    'User ID who created the referral';
COMMENT ON COLUMN referral_state_manager.updated_by IS 
    'User ID who last updated the referral';

-- ============================================================================
-- Table: referral_state_history
-- ============================================================================
-- Audit trail table for tracking all state transitions

CREATE TABLE IF NOT EXISTS referral_state_history (
    id SERIAL PRIMARY KEY,
    referral_id VARCHAR(255) NOT NULL,
    from_state VARCHAR(50),
    to_state VARCHAR(50) NOT NULL,
    transitioned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    transitioned_by VARCHAR(255),
    reason TEXT,
    CONSTRAINT fk_referral_state_history_referral_id 
        FOREIGN KEY (referral_id) 
        REFERENCES referral_state_manager(referral_id) 
        ON DELETE CASCADE
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_referral_state_history_id 
    ON referral_state_history(id);
CREATE INDEX IF NOT EXISTS idx_referral_state_history_referral_id 
    ON referral_state_history(referral_id);
CREATE INDEX IF NOT EXISTS idx_referral_state_history_transitioned_at 
    ON referral_state_history(transitioned_at);
CREATE INDEX IF NOT EXISTS idx_referral_state_history_to_state 
    ON referral_state_history(to_state);

-- Add comment to table
COMMENT ON TABLE referral_state_history IS 
    'Audit trail table for tracking all state transitions';

COMMENT ON COLUMN referral_state_history.id IS 
    'Primary key: Auto-incrementing ID for each state transition record';
COMMENT ON COLUMN referral_state_history.referral_id IS 
    'Foreign key to referral_state_manager.referral_id';
COMMENT ON COLUMN referral_state_history.from_state IS 
    'Previous state (NULL for initial state)';
COMMENT ON COLUMN referral_state_history.to_state IS 
    'New state after transition';
COMMENT ON COLUMN referral_state_history.transitioned_at IS 
    'Timestamp when the state transition occurred';
COMMENT ON COLUMN referral_state_history.transitioned_by IS 
    'User ID who triggered the state transition';
COMMENT ON COLUMN referral_state_history.reason IS 
    'Optional reason or notes for the state change';

-- ============================================================================
-- Verification Query (optional - run after creating tables)
-- ============================================================================
-- Uncomment and run to verify tables were created:

-- SELECT 
--     table_name,
--     (SELECT COUNT(*) FROM information_schema.columns 
--      WHERE table_name = t.table_name) as column_count
-- FROM information_schema.tables t
-- WHERE table_schema = 'public' 
-- AND table_name IN ('referral_state_manager', 'referral_state_history')
-- ORDER BY table_name;
