# E.Y.T ERP — Production Go-Live Runbook

This runbook moves the already-tested Docker stack from GitHub to the IranServer Linux VPS without placing passwords, tokens, database credentials, or customer data in the repository.

## 1. VPS prerequisites

- Ubuntu/Debian Linux VPS
- Docker Engine and Docker Compose plugin
- Git
- Open TCP ports 80 and 443
- DNS records pointing to the VPS:
  - `eytparts.ir`
  - `app.eytparts.ir`
  - `api.eytparts.ir`

Do not expose PostgreSQL port 5432 to the public internet.

## 2. Get the release

```bash
git clone https://github.com/eytcar-creator/Eyt-erp.git /opt/eyt-erp
cd /opt/eyt-erp
git checkout main
git pull --ff-only origin main
```

For a controlled release, pin the deployment to a tested tag instead of an arbitrary branch commit.

## 3. Configure secrets outside Git

Create `/opt/eyt-erp/.env` with production-only values. At minimum:

```env
POSTGRES_DB=eyt_erp
POSTGRES_USER=eyt_erp
POSTGRES_PASSWORD=<strong-random-password>
DATABASE_URL=postgresql://eyt_erp:<same-password>@db:5432/eyt_erp
```

Set file permissions:

```bash
chmod 600 /opt/eyt-erp/.env
```

Never commit `.env` or real credentials.

## 4. Start the production stack

```bash
docker compose --env-file .env -f docker-compose.production.yml up -d --build
```

Migration runs before API startup through the production Compose dependency chain.

## 5. Verify health and readiness

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/ready
```

Then run:

```bash
BASE_URL=http://127.0.0.1:8000 python scripts/operational_smoke_test.py
```

## 6. Reverse proxy and TLS

Put Nginx/Caddy/another hardened reverse proxy in front of the application. Terminate TLS there and route:

- `https://app.eytparts.ir` → Catalog/UI
- `https://api.eytparts.ir` → API

Only ports 80/443 should be internet-facing. Do not publish the PostgreSQL service.

## 7. First controlled business test

Use a test/staging database or a controlled production test document. Do not use real customer transactions until the full path is verified.

Test the inventory lifecycle:

1. Receive raw material.
2. Confirm balance.
3. Reserve material against a production document.
4. Confirm available quantity decreases by the reservation.
5. Issue material to production.
6. Confirm on-hand quantity decreases.
7. Record production completion and QC.
8. Release only accepted finished quantity to finished-goods inventory.
9. Confirm final balance and audit trail.

Recommended first manufacturing scenario: `EYT-ARIO-TIE-ROD`, production order `PO-ARIO-0001`, target quantity 2000.

## 8. Go-live gate

Go live only when all of these are green:

- [ ] DNS resolves for `app.eytparts.ir` and `api.eytparts.ir`
- [ ] TLS certificate valid
- [ ] `/health` returns 200
- [ ] `/ready` returns 200
- [ ] migration completed successfully
- [ ] authenticated login/RBAC works
- [ ] inventory receive/reserve/issue/balance works against PostgreSQL
- [ ] production order lifecycle works
- [ ] QC blocks failed final release
- [ ] finished-goods receipt works
- [ ] audit logs are written
- [ ] backup and restore procedure tested
- [ ] no production secrets exist in Git

## 9. Rollback

Keep the previous known-good image/release available. Before upgrading, record the deployed Git commit and database backup status. Never roll back application code across an incompatible database migration without the corresponding database rollback plan.
