-- as admin — should affect 1 row
SET request.jwt.claims = '{"sub": "c1111111-1111-1111-1111-111111111111", "role": "authenticated"}';
DELETE FROM calls
WHERE id = (
    SELECT id FROM calls
    WHERE org_id = 'a1111111-1111-1111-1111-111111111111'
    LIMIT 1
);