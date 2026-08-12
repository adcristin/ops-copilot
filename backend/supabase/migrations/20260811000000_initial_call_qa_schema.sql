-- =============================================================================
-- Call QA Dashboard Initial Schema
-- =============================================================================

-- 1. Tables
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE users_orgs (
    user_id UUID REFERENCES auth.users ON DELETE CASCADE,
    org_id UUID REFERENCES organizations ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('admin', 'member')),
    PRIMARY KEY (user_id, org_id)
);

CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations ON DELETE CASCADE,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations ON DELETE CASCADE,
    agent_id UUID REFERENCES agents ON DELETE SET NULL,
    call_date TIMESTAMPTZ NOT NULL,
    duration_seconds INT,
    audio_url TEXT,
    transcript TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'transcribing', 'scoring', 'scored', 'failed')),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE call_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID REFERENCES calls ON DELETE CASCADE UNIQUE,
    greeting_score NUMERIC(5,2) CHECK (greeting_score BETWEEN 0 AND 100),
    compliance_score NUMERIC(5,2) CHECK (compliance_score BETWEEN 0 AND 100),
    resolution_score NUMERIC(5,2) CHECK (resolution_score BETWEEN 0 AND 100),
    tone_score NUMERIC(5,2) CHECK (tone_score BETWEEN 0 AND 100),
    -- Computed average of the 4 sub-scores
    overall_score NUMERIC(5,2) GENERATED ALWAYS AS (
        (greeting_score + compliance_score + resolution_score + tone_score) / 4
    ) STORED,
    flagged BOOLEAN DEFAULT false,
    flag_reason TEXT,
    rubric_notes JSONB DEFAULT '{}'::jsonb,
    scored_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Indexes
CREATE INDEX idx_calls_org_date ON calls (org_id, call_date);
CREATE INDEX idx_call_scores_call_id ON call_scores (call_id);

-- 3. Security: Row Level Security (RLS)

CREATE OR REPLACE FUNCTION get_my_orgs()
RETURNS UUID[] AS $$
    SELECT array_agg(org_id) FROM users_orgs WHERE user_id = auth.uid();
$$ LANGUAGE sql STABLE;

ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE users_orgs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_scores ENABLE ROW LEVEL SECURITY;

-- Organization/Membership Policies
CREATE POLICY "Users can view their own organizations" ON organizations FOR SELECT USING (id = ANY (get_my_orgs()));
CREATE POLICY "Users can view their own memberships" ON users_orgs FOR SELECT USING (user_id = auth.uid());

-- Agent Policies
CREATE POLICY "Users can view agents in their orgs" ON agents FOR SELECT USING (org_id = ANY (get_my_orgs()));

-- Call Policies
CREATE POLICY "Users can view calls in their orgs"
ON calls FOR SELECT USING (org_id = ANY (get_my_orgs()));

CREATE POLICY "Admins can update calls in their org"
ON calls FOR UPDATE
USING (
  EXISTS (
    SELECT 1 FROM users_orgs
    WHERE user_id = auth.uid()
      AND org_id = calls.org_id
      AND role = 'admin'
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1 FROM users_orgs
    WHERE user_id = auth.uid()
      AND org_id = calls.org_id
      AND role = 'admin'
  )
);

CREATE POLICY "Admins can delete calls in their org"
ON calls FOR DELETE
USING (
  EXISTS (
    SELECT 1 FROM users_orgs
    WHERE user_id = auth.uid()
      AND org_id = calls.org_id
      AND role = 'admin'
  )
);

-- Call Score Policies
CREATE POLICY "Users can view scores for calls in their orgs"
ON call_scores FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM calls
        WHERE calls.id = call_scores.call_id
        AND calls.org_id = ANY (get_my_orgs())
    )
);
