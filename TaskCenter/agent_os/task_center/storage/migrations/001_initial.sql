-- Enable UUID generation extension
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Main tasks table storing task metadata and DAG structure
CREATE TABLE tasks (
    id          UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255)  NOT NULL,
    description TEXT,
    role        VARCHAR(64)   NOT NULL,
    status      VARCHAR(32)   NOT NULL,
    depends_on  JSONB         DEFAULT '[]'::jsonb,
    children    JSONB         DEFAULT '[]'::jsonb,
    result      JSONB,
    metadata    JSONB         DEFAULT '{}'::jsonb,
    created_at  BIGINT        NOT NULL,
    updated_at  BIGINT        NOT NULL,
    version     INT           NOT NULL DEFAULT 0
);

-- Indexes for common query patterns
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_role ON tasks(role);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);

-- Runtime state table for mutable execution state
CREATE TABLE task_runtime_states (
    task_id      UUID          PRIMARY KEY,
    runtime_data JSONB         NOT NULL DEFAULT '{}'::jsonb,
    version      INT           NOT NULL DEFAULT 0,
    updated_at   BIGINT        NOT NULL
);

-- Index for temporal queries
CREATE INDEX idx_task_runtime_states_updated_at ON task_runtime_states(updated_at);