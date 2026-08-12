SET request.jwt.claims = '{"sub": "c1111111-1111-1111-1111-111111111111", "role": "authenticated"}';

SELECT EXISTS (
    SELECT 1 FROM users_orgs
    WHERE user_id = auth.uid()
      AND org_id = 'a1111111-1111-1111-1111-111111111111'
      AND role = 'admin'
);
