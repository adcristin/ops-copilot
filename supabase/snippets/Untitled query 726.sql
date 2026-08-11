SET request.jwt.claims = '{"sub": "c1111111-1111-1111-1111-111111111111", "role": "authenticated"}';
DELETE FROM calls
WHERE id = (
    SELECT id FROM calls
    WHERE org_id = 'a1111111-1111-1111-1111-111111111111'
    LIMIT 1
);

SELECT auth.uid();

SET request.jwt.claims = '{"sub": "c2222222-2222-2222-2222-222222222222", "role": "authenticated"}';
DELETE FROM calls
WHERE id = (
    SELECT id FROM calls
    WHERE org_id = 'a1111111-1111-1111-1111-111111111111'
    LIMIT 1
);