# E.Y.T Catalog Production Deployment

## معماری
Internet -> HTTPS reverse proxy -> Catalog (port 8080) -> /api -> ERP API (port 8000) -> PostgreSQL

## 1. DNS
Create an A record for `eyt-catalog.ir` pointing to the VPS public IP.

## 2. Environment
Create `.env` from the production environment template and set strong production values. Never commit secrets.

Required:
- POSTGRES_PASSWORD
- DATABASE_URL
- JWT_SECRET
- BOOTSTRAP_SECRET

## 3. Start stack
```bash
git pull origin main
docker compose -f docker-compose.production.yml up -d --build
docker compose -f docker-compose.production.yml ps
curl -f http://127.0.0.1:8000/health
curl -f http://127.0.0.1:8000/ready
curl -f http://127.0.0.1:8080/
```

## 4. HTTPS proxy
Put Nginx/Caddy in front of the VPS. Route:
- `/` -> `http://127.0.0.1:8080`
- `/api/` -> `http://127.0.0.1:8080/api/`

Enable TLS for `eyt-catalog.ir`.

## 5. Acceptance test
1. Open the catalog on mobile.
2. Authenticate as a real customer.
3. Select a real Product UUID from Master Data.
4. Submit an order.
5. Verify the order in Order Center.
6. Confirm downstream production/QC tracking.
7. Verify the order from a second device.

A production launch is complete only after this end-to-end test passes.
