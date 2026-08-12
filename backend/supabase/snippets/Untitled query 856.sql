-- Simulate a 'member' role for a specific user_id/org_id
SET request.jwt.claims = '{"sub": "<some-member-user-uuid>", "role": "authenticated"}';

-- Try to delete a call — should FAIL if RLS is working
DELETE FROM calls WHERE id = '<some-call-uuid>';