-- Seed data for Call QA Dashboard

-- 1. Create Organizations
INSERT INTO organizations (id, name) VALUES
('a1111111-1111-1111-1111-111111111111', 'Global Logistics Corp'),
('a2222222-2222-2222-2222-222222222222', 'HealthFirst Insurance');

-- 2. Create Agents
INSERT INTO agents (id, org_id, name, email) VALUES
('b1111111-1111-1111-1111-111111111111', 'a1111111-1111-1111-1111-111111111111', 'Sarah Jenkins', 'sarah.j@globallogistics.com'),
('b2222222-2222-2222-2222-222222222222', 'a1111111-1111-1111-1111-111111111111', 'Mike Ross', 'mike.r@globallogistics.com'),
('b3333333-3333-3333-3333-333333333333', 'a2222222-2222-2222-2222-222222222222', 'Elena Rodriguez', 'elena.r@healthfirst.com'),
('b4444444-4444-4444-4444-444444444444', 'a2222222-2222-2222-2222-222222222222', 'David Chen', 'david.c@healthfirst.com');

-- 2.4 Create fake auth users (required — users_orgs.user_id has an FK to auth.users)
INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at, raw_app_meta_data, raw_user_meta_data, aud, role)
VALUES
('c1111111-1111-1111-1111-111111111111', 'admin1@globallogistics.com', crypt('password123', gen_salt('bf')), now(), now(), now(), '{"provider":"email","providers":["email"]}', '{}', 'authenticated', 'authenticated'),
('c2222222-2222-2222-2222-222222222222', 'member1@globallogistics.com', crypt('password123', gen_salt('bf')), now(), now(), now(), '{"provider":"email","providers":["email"]}', '{}', 'authenticated', 'authenticated'),
('c3333333-3333-3333-3333-333333333333', 'admin2@healthfirst.com', crypt('password123', gen_salt('bf')), now(), now(), now(), '{"provider":"email","providers":["email"]}', '{}', 'authenticated', 'authenticated'),
('c4444444-4444-4444-4444-444444444444', 'member2@healthfirst.com', crypt('password123', gen_salt('bf')), now(), now(), now(), '{"provider":"email","providers":["email"]}', '{}', 'authenticated', 'authenticated')
ON CONFLICT (id) DO NOTHING;

-- 2.5 Create User-Org Memberships (needed for RLS to work at all)
INSERT INTO users_orgs (user_id, org_id, role) VALUES
('c1111111-1111-1111-1111-111111111111', 'a1111111-1111-1111-1111-111111111111', 'admin'),
('c2222222-2222-2222-2222-222222222222', 'a1111111-1111-1111-1111-111111111111', 'member'),
('c3333333-3333-3333-3333-333333333333', 'a2222222-2222-2222-2222-222222222222', 'admin'),
('c4444444-4444-4444-4444-444444444444', 'a2222222-2222-2222-2222-222222222222', 'member');

-- 3. Create Calls
INSERT INTO calls (id, org_id, agent_id, call_date, duration_seconds, status) VALUES
(gen_random_uuid(), 'a1111111-1111-1111-1111-111111111111', 'b1111111-1111-1111-1111-111111111111', '2026-08-01 10:00:00Z', 320, 'scored'),
(gen_random_uuid(), 'a1111111-1111-1111-1111-111111111111', 'b1111111-1111-1111-1111-111111111111', '2026-08-01 11:15:00Z', 450, 'scored'),
(gen_random_uuid(), 'a1111111-1111-1111-1111-111111111111', 'b1111111-1111-1111-1111-111111111111', '2026-08-02 09:30:00Z', 120, 'failed'),
(gen_random_uuid(), 'a1111111-1111-1111-1111-111111111111', 'b2222222-2222-2222-2222-222222222222', '2026-08-02 14:00:00Z', 600, 'scored'),
(gen_random_uuid(), 'a1111111-1111-1111-1111-111111111111', 'b2222222-2222-2222-2222-222222222222', '2026-08-03 10:00:00Z', 300, 'scoring'),
(gen_random_uuid(), 'a1111111-1111-1111-1111-111111111111', 'b2222222-2222-2222-2222-222222222222', '2026-08-03 11:00:00Z', 410, 'scored'),
(gen_random_uuid(), 'a1111111-1111-1111-1111-111111111111', 'b1111111-1111-1111-1111-111111111111', '2026-08-04 08:45:00Z', 200, 'scored'),
(gen_random_uuid(), 'a1111111-1111-1111-1111-111111111111', 'b1111111-1111-1111-1111-111111111111', '2026-08-04 15:30:00Z', 380, 'scored'),
(gen_random_uuid(), 'a1111111-1111-1111-1111-111111111111', 'b2222222-2222-2222-2222-222222222222', '2026-08-05 12:00:00Z', 500, 'transcribing'),
(gen_random_uuid(), 'a2222222-2222-2222-2222-222222222222', 'b3333333-3333-3333-3333-333333333333', '2026-08-01 09:00:00Z', 420, 'scored'),
(gen_random_uuid(), 'a2222222-2222-2222-2222-222222222222', 'b3333333-3333-3333-3333-333333333333', '2026-08-01 13:00:00Z', 210, 'scored'),
(gen_random_uuid(), 'a2222222-2222-2222-2222-222222222222', 'b3333333-3333-3333-3333-333333333333', '2026-08-02 10:00:00Z', 550, 'scored'),
(gen_random_uuid(), 'a2222222-2222-2222-2222-222222222222', 'b4444444-4444-4444-4444-444444444444', '2026-08-02 11:00:00Z', 300, 'scored'),
(gen_random_uuid(), 'a2222222-2222-2222-2222-222222222222', 'b4444444-4444-4444-4444-444444444444', '2026-08-03 15:00:00Z', 480, 'scored'),
(gen_random_uuid(), 'a2222222-2222-2222-2222-222222222222', 'b4444444-4444-4444-4444-444444444444', '2026-08-04 09:00:00Z', 180, 'pending'),
(gen_random_uuid(), 'a2222222-2222-2222-2222-222222222222', 'b3333333-3333-3333-3333-333333333333', '2026-08-04 14:00:00Z', 360, 'scored'),
(gen_random_uuid(), 'a2222222-2222-2222-2222-222222222222', 'b3333333-3333-3333-3333-333333333333', '2026-08-05 11:00:00Z', 410, 'scored'),
(gen_random_uuid(), 'a2222222-2222-2222-2222-222222222222', 'b4444444-4444-4444-4444-444444444444', '2026-08-05 16:00:00Z', 290, 'scored');

-- 4. Create Scores
INSERT INTO call_scores (call_id, greeting_score, compliance_score, resolution_score, tone_score, flagged, flag_reason, rubric_notes)
SELECT
    id,
    (random() * 30 + 70),
    (random() * 40 + 60),
    (random() * 50 + 50),
    (random() * 20 + 80),
    (random() < 0.2),
    CASE WHEN random() < 0.2 THEN 'Failed to verify customer identity' ELSE NULL END,
    '{"feedback": "Agent was professional but struggled with resolution steps"}'::jsonb
FROM calls
WHERE status = 'scored';
