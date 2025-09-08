-- Database extensions for RapidTrader reliability features
-- Run with: docker exec -i rapidtrader-db psql -U postgres -d rapidtrader < scripts/setup_db_extensions.sql

-- Track system kill state and when trading should resume
CREATE TABLE IF NOT EXISTS system_state (
    d DATE PRIMARY KEY,
    kill_active BOOLEAN NOT NULL DEFAULT FALSE,
    reason TEXT,
    resume_eligible_d DATE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Optional: paper/live execution table (for future reconciliation)
CREATE TABLE IF NOT EXISTS exec_fills (
    id BIGSERIAL PRIMARY KEY,
    d DATE NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,           -- buy/sell
    qty INTEGER NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    status TEXT NOT NULL,         -- filled/partial/canceled
    venue TEXT,                   -- 'alpaca_paper', 'alpaca_live', etc.
    broker_order_id TEXT,
    strategy TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Update triggers for timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to system_state
DROP TRIGGER IF EXISTS update_system_state_updated_at ON system_state;
CREATE TRIGGER update_system_state_updated_at 
    BEFORE UPDATE ON system_state 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Add indexes for performance (after tables are created)
CREATE INDEX IF NOT EXISTS idx_system_state_d ON system_state(d);
CREATE INDEX IF NOT EXISTS idx_exec_fills_d_symbol ON exec_fills(d, symbol);
CREATE INDEX IF NOT EXISTS idx_exec_fills_broker_order_id ON exec_fills(broker_order_id);

-- Insert some helpful comments
COMMENT ON TABLE system_state IS 'Tracks kill switch state and trading permissions by date';
COMMENT ON TABLE exec_fills IS 'Records actual broker executions for reconciliation';
COMMENT ON COLUMN system_state.kill_active IS 'Whether new position entries are blocked';
COMMENT ON COLUMN system_state.reason IS 'Reason for kill switch activation (e.g., "Sharpe < -1.0")';
COMMENT ON COLUMN exec_fills.venue IS 'Broker venue identifier for tracking execution source';
