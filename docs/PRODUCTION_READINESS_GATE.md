# E.Y.T ERP — Production Readiness Gate

**Status:** OPEN — audit required before production promotion  
**Purpose:** Establish evidence-based release gates for operating E.Y.T ERP with real company data.  
**Safety rule:** This checklist is not proof of deployment. Do not claim a check passed until its evidence is attached.

## 1. Current evidence from repository review

- The repository includes a production Docker Compose definition with PostgreSQL, a migration service, API, finance worker, catalog, and optional n8n.
- The API container is bound to `127.0.0.1:8000`; catalog is bound to `127.0.0.1:8080`. Public access therefore depends on a separately configured reverse proxy/tunnel and TLS.
- The compose file requires runtime secrets including `POSTGRES_PASSWORD`, `DATABASE_URL`, `JWT_SECRET`, `BOOTSTRAP_SECRET`, `RUBIKA_WORKSHOP_WEBHOOK_SECRET`; automation also requires `N8N_ENCRYPTION_KEY` and `EYT_ERP_CHANNEL_TOKEN`.
- The compose migration service runs `scripts/migrate_production.py` before the API starts.
- Repository evidence alone cannot establish that a live server, DNS, TLS, database, backup, or external channel integration is working.
- No production deployment, production database migration, or live smoke test is asserted by this document.

## 2. Gate A — repository and CI

- [ ] Confirm the target commit is on `main` and record its SHA.
- [ ] Confirm all required GitHub Actions workflows have passed for that exact commit.
- [ ] Confirm no required review or branch protection check is bypassed.
- [ ] Run migration-chain verification from an empty test database through the latest migration.
- [ ] Run integration tests for authentication/RBAC, product master, inventory/reservations, procurement, production, sales/fulfilment, and finance.
- [ ] Run production Compose smoke test with non-production test secrets.
- [ ] Record failures and their remediation; do not substitute a code review for execution evidence.

## 3. Gate B — deployment configuration

- [ ] Identify the actual host/provider and deployment directory.
- [ ] Verify DNS records for intended public hostnames.
- [ ] Verify reverse proxy configuration and valid TLS certificates.
- [ ] Verify secrets are injected by the host environment or secret manager, not committed to Git.
- [ ] Verify database persistence volume and least-privilege network exposure.
- [ ] Verify the API and catalog are not accidentally exposed directly on public interfaces.
- [ ] Verify application logs exclude passwords, tokens, customer secrets, and unnecessary personal data.
- [ ] Confirm the installed application commit SHA matches the approved release.

## 4. Gate C — database, backup and recovery

- [ ] Take a consistent backup before any production migration.
- [ ] Record database version and current migration head.
- [ ] Run migrations using the production migration process, after backup and approval.
- [ ] Verify migration head and schema compatibility after migration.
- [ ] Restore the backup into an isolated environment and verify application-readable data.
- [ ] Record backup location, retention, restore duration, and responsible role.
- [ ] Never test restore by overwriting the live database.

## 5. Gate D — end-to-end pilot order

Use a designated test customer/product in a controlled environment first. Do not create fake operational records in the live company database.

- [ ] Resolve an existing customer and product without creating duplicates.
- [ ] Resolve the authoritative customer price server-side.
- [ ] Verify physical stock, existing reservations, credit/hold rules, and expected gate result.
- [ ] Submit one idempotent order through the intended intake channel.
- [ ] Confirm reservation is created once and available stock is correct.
- [ ] If stock is short, verify the system reports a production/purchasing need without silently inventing stock.
- [ ] For a production route, record BOM revision, material consumption, routing operations, contractor costs, and batch ID.
- [ ] Record QC results and block release when mandatory checks fail.
- [ ] Issue/fulfil the order once; verify its reservation is consumed once and inventory is issued once.
- [ ] Verify invoice, receivable, payment/collection, and cost/profit report reconcile.
- [ ] Verify audit events and order status transitions are traceable end-to-end.

## 6. Gate E — E.Y.T master data integrity

- [ ] Export Product Master and Category Tree read-only from the actual ERP.
- [ ] Preserve existing product UUIDs, SKUs, product codes, and barcode values.
- [ ] Reconcile aliases, OEM references, vehicle fitments, and duplicate candidates.
- [ ] Reconcile product family categories, especially overlap between `FRONT_SUSPENSION` and `CONTROL_ARM`.
- [ ] Link existing BOM/routing/QC documents to actual product records only after verification.
- [ ] Keep unknown data as `VERIFY` / `UNKNOWN`; do not infer missing dimensions, materials, costs, or fitments.
- [ ] Do not add “سه‌شاخ” to the E.Y.T product catalog.

## 7. Release decision

Release is **BLOCKED** until Gates A–D have evidence and an accountable reviewer records a go/no-go decision. Gate E must be complete for any product or process included in the pilot.

Evidence record:
- Release commit SHA:
- CI run links:
- Host / environment:
- Migration head before / after:
- Backup and restore evidence:
- Health / readiness results:
- Pilot order reference (test environment):
- Known limitations:
- Reviewer and date:
- Decision: `GO` / `NO-GO`

## 8. Safe operational commands

Run only on the intended host, after confirming the working directory and reviewing the environment file. Never paste secrets into tickets or chat.

```bash
docker compose -f docker-compose.production.yml config --quiet
docker compose -f docker-compose.production.yml ps
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/ready
```

The first command validates Compose configuration; it does not prove that services are running. Health/readiness checks must be run on the actual host. Do not run `docker compose up`, migrations, or restore operations against production until backup and release gates are satisfied.
