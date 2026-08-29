-- E.Y.T ERP Identity / RBAC / refresh-token / audit layer
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS eyt_users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  username varchar(120) NOT NULL UNIQUE,
  email varchar(250) UNIQUE,
  password_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_login_at timestamptz
);
CREATE TABLE IF NOT EXISTS eyt_roles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name varchar(120) NOT NULL UNIQUE,
  description text
);
CREATE TABLE IF NOT EXISTS eyt_permissions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(150) NOT NULL UNIQUE,
  description text
);
CREATE TABLE IF NOT EXISTS eyt_user_roles (
  user_id uuid NOT NULL REFERENCES eyt_users(id) ON DELETE CASCADE,
  role_id uuid NOT NULL REFERENCES eyt_roles(id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, role_id)
);
CREATE TABLE IF NOT EXISTS eyt_role_permissions (
  role_id uuid NOT NULL REFERENCES eyt_roles(id) ON DELETE CASCADE,
  permission_id uuid NOT NULL REFERENCES eyt_permissions(id) ON DELETE CASCADE,
  PRIMARY KEY (role_id, permission_id)
);
CREATE TABLE IF NOT EXISTS eyt_refresh_tokens (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES eyt_users(id) ON DELETE CASCADE,
  token_hash varchar(128) NOT NULL UNIQUE,
  expires_at timestamptz NOT NULL,
  revoked_at timestamptz,
  replaced_by_id uuid,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS eyt_audit_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_user_id uuid REFERENCES eyt_users(id) ON DELETE SET NULL,
  action varchar(120) NOT NULL,
  entity_id uuid,
  correlation_id varchar(120),
  ip_address varchar(64),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO eyt_roles(name,description) VALUES ('CEO','Full internal ERP access') ON CONFLICT (name) DO NOTHING;
INSERT INTO eyt_permissions(code) VALUES
 ('production.read'),('production.execute'),('qc.inspect'),('qc.release'),
 ('reporting.read'),('admin.users.manage'),('admin.roles.manage'),
 ('product.read'),('product.write'),('inventory.read'),('inventory.execute'),
 ('inventory.write'),('procurement.read')
ON CONFLICT (code) DO NOTHING;
INSERT INTO eyt_role_permissions(role_id,permission_id)
SELECT r.id,p.id FROM eyt_roles r CROSS JOIN eyt_permissions p WHERE r.name='CEO'
ON CONFLICT DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_eyt_refresh_user ON eyt_refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_eyt_audit_actor_time ON eyt_audit_logs(actor_user_id,created_at);
