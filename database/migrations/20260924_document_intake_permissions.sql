INSERT INTO eyt_permissions(code)
VALUES ('document.intake'), ('document.intake.read')
ON CONFLICT (code) DO NOTHING;

INSERT INTO eyt_role_permissions(role_id, permission_id)
SELECT r.id, p.id
FROM eyt_roles r
CROSS JOIN eyt_permissions p
WHERE r.name = 'CEO'
  AND p.code IN ('document.intake','document.intake.read')
ON CONFLICT DO NOTHING;
