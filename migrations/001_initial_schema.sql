-- Sessions table
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    message_count INT NOT NULL DEFAULT 0
);

CREATE INDEX idx_sessions_last_active ON sessions(last_active_at DESC);

-- Conversation history
CREATE TABLE conversation_history (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    token_count INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_history_session ON conversation_history(session_id, created_at);

-- Tool call log
CREATE TABLE tool_call_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    message_id UUID REFERENCES conversation_history(message_id),
    tool_name TEXT NOT NULL,
    input_args JSONB NOT NULL,
    output_summary TEXT,
    duration_ms INT,
    cached BOOLEAN NOT NULL DEFAULT FALSE,
    called_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tool_calls_session ON tool_call_log(session_id, called_at);
CREATE INDEX idx_tool_calls_tool ON tool_call_log(tool_name);

-- API usage tracking
CREATE TABLE api_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_name TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    status_code INT NOT NULL,
    response_time_ms INT,
    rate_limit_remaining INT,
    rate_limit_reset_at TIMESTAMPTZ,
    called_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_usage_name ON api_usage(api_name, called_at DESC);

-- Cached API responses
CREATE TABLE cached_api_responses (
    cache_key TEXT PRIMARY KEY,
    api_name TEXT NOT NULL,
    query TEXT NOT NULL,
    response_data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_cache_expires ON cached_api_responses(expires_at);