-- Week-one ledger. Scoped by run_id; admission is single-coordinator only.
CREATE TABLE IF NOT EXISTS transactions (
    run_id TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    PRIMARY KEY (run_id, transaction_id)
);

CREATE TABLE IF NOT EXISTS effect_intents (
    run_id TEXT NOT NULL,
    effect_id TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    logical_operation_id TEXT NOT NULL,
    intent JSONB NOT NULL,
    certainty TEXT NOT NULL CHECK (
        certainty IN ('NOT_STARTED', 'PENDING', 'CONFIRMED', 'FAILED', 'UNKNOWN', 'COMPENSATED')
    ),
    PRIMARY KEY (run_id, effect_id),
    UNIQUE (run_id, logical_operation_id),
    FOREIGN KEY (run_id, transaction_id) REFERENCES transactions(run_id, transaction_id)
);

CREATE TABLE IF NOT EXISTS effect_observations (
    observation_id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL,
    effect_id TEXT NOT NULL,
    observation TEXT NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (run_id, effect_id) REFERENCES effect_intents(run_id, effect_id)
);

CREATE TABLE IF NOT EXISTS effect_events (
    event_id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL,
    effect_id TEXT NOT NULL,
    event JSONB NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (run_id, effect_id) REFERENCES effect_intents(run_id, effect_id)
);
CREATE INDEX IF NOT EXISTS effect_events_run_idx ON effect_events(run_id, event_id);

CREATE OR REPLACE FUNCTION agenttxn_reject_event_mutation() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'effect_events is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS effect_events_append_only ON effect_events;
CREATE TRIGGER effect_events_append_only BEFORE UPDATE OR DELETE ON effect_events
    FOR EACH ROW EXECUTE FUNCTION agenttxn_reject_event_mutation();
