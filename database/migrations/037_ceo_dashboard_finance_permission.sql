-- E.Y.T ERP | Migration 037 | CEO dashboard finance permission
BEGIN;
INSERT INTO eyt_permissions(code) VALUES ('finance.read') ON CONFLICT (code) DO NOTHING;
INSERT INTO eyt_role_permissions(role_id, permission_id)
SELECT r.id, p.id
FROM eyt_roles r CROSS JOIN eyt_permissions p
WHERE r.name='CEO' AND p.code='finance.read'
ON CONFLICT DO NOTHING;
COMMIT;
