SELECT uo.user_id, uo.org_id, uo.role, u.email
FROM users_orgs uo
JOIN auth.users u ON u.id = uo.user_id
ORDER BY uo.role;