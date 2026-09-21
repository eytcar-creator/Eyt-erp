# E.Y.T Production Deployment Checklist

## 1. Firebase / Firestore

Project: `eyt-catalog`

- [x] Firestore rules are versioned in `firestore.rules`
- [x] Test Mode expiration rule is not restored
- [ ] Authenticate Firebase CLI
- [ ] Deploy rules: `firebase deploy --only firestore:rules`
- [ ] Verify public catalog reads and denied writes

Required operator access: Firebase project owner/editor or equivalent deployment permission.

## 2. ERP API + PostgreSQL

The production stack is defined in `docker-compose.production.yml`.

Required runtime secrets:

- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `JWT_SECRET`
- `BOOTSTRAP_SECRET`

Deployment sequence:

1. Provision a Docker-capable host.
2. Set secrets in the host environment, never in Git.
3. Run migrations.
4. Start API and catalog containers.
5. Verify `/health`.
6. Verify `/ready`.
7. Verify `/api/v1/catalog/vehicles`.
8. Verify customer login/order flow.

No VPS purchase is implied by this repository. The host can be an existing Docker-capable server.

## 3. Catalog domain

Target: `eyt-catalog.ir`

Preferred production routing:

`eyt-catalog.ir -> reverse proxy -> catalog container`

The catalog uses same-origin `/api/v1`; nginx proxies API requests to the ERP API container. This avoids exposing credentials in browser configuration.

DNS and TLS must be configured at the actual DNS/hosting provider. No provider credentials are stored in this repository.

## 4. Final E2E acceptance

- [ ] Open catalog over HTTPS
- [ ] Vehicle list loads from PostgreSQL Master Data
- [ ] Confirmed fitments load
- [ ] Customer login works
- [ ] Customer-specific prices load
- [ ] Order creates exactly once
- [ ] Order appears in customer history
- [ ] Tracking returns the same order
- [ ] Unauthorized customer cannot read another customer's order
- [ ] Public catalog never exposes internal cost, supplier, margin, or purchasing data
- [ ] Firebase writes remain denied

## Stop conditions

Do not declare production live until all external checks above pass. Repository readiness is not the same thing as infrastructure deployment.
