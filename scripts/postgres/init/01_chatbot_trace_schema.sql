CREATE TABLE IF NOT EXISTS chatbot_trace_events (
    id BIGSERIAL PRIMARY KEY,
    trace_id TEXT NOT NULL,
    event_index INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chatbot_trace_events_trace_id_event_index
ON chatbot_trace_events(trace_id, event_index);
