# E.Y.T ERP Production Go-Live Runbook

گیت‌های اجباری:
- DNS: eytparts.ir / app.eytparts.ir / api.eytparts.ir
- TLS معتبر
- /health و /ready = 200
- migration موفق
- login/RBAC
- خرید، دریافت و موجودی
- تولید و WIP
- QC و جلوگیری از آزادسازی مردود
- Finished Goods
- audit log
- backup/restore تست‌شده
- هیچ secret واقعی در Git

استقرار روی IranServer باید با Docker/PostgreSQL و secret خارج از Git انجام شود. PostgreSQL عمومی نشود.

فرمان‌های اجرایی:
git clone https://github.com/eytcar-creator/Eyt-erp.git /opt/eyt-erp
cd /opt/eyt-erp
git checkout main
cp .env.example .env
chmod 600 .env
docker compose --env-file .env -f docker-compose.production.yml up -d --build
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/ready
BASE_URL=http://127.0.0.1:8000 python scripts/operational_smoke_test.py

سناریوی کنترل‌شده اولیه: آریو 2000 عدد، از دریافت مواد تا تولید، QC، موجودی محصول نهایی، فروش، فاکتور و وصول.
