# E.Y.T ERP & Auto Parts

سیستم ERP عملیاتی E.Y.T برای مدیریت قطعات، انبار، تولید، خرید، فروش، مالی و کنترل کیفیت.

## وضعیت فعلی

- Backend عملیاتی بر پایه FastAPI
- PostgreSQL به‌عنوان دیتابیس عملیاتی
- احراز هویت و RBAC
- ثبت رویدادهای قابل ممیزی
- مدیریت موجودی، رزرو و گردش کالا
- BOM و نسخه‌بندی آن
- سفارش تولید و عملیات تولید
- محاسبه هزینه تولید و هزینه‌های پیمانکاری
- خرید، فروش، مالی و داشبورد عملیاتی
- health/readiness probe برای استقرار
- Docker Compose برای اجرای محیط عملیاتی

## اجرای محلی

پیش‌نیاز: Docker و Docker Compose.

1. فایل نمونه محیط را به `.env` تبدیل کنید.
2. حداقل `POSTGRES_PASSWORD` و `DATABASE_URL` را با مقادیر واقعی محیط خود تنظیم کنید.
3. اجرا:

```bash
docker compose -f docker-compose.production.yml up -d --build
```

4. سلامت سرویس:

```bash
curl http://localhost:8000/health
```

5. آمادگی دیتابیس:

```bash
curl http://localhost:8000/ready
```

## اصل مهم داده واقعی

این مخزن هیچ رمز عبور، توکن، کلید API یا اطلاعات مشتری واقعی را commit نمی‌کند. داده‌های واقعی باید فقط از طریق محیط اجرا یا فرآیند import کنترل‌شده وارد شوند.

## مسیر عملیاتی E.Y.T

Master Data → Procurement → Receiving → Inventory → BOM → Production → QC → Finished Goods → Sales → Receivables → Dashboard

جزئیات API تولید در `api/production/README.md` و قرارداد API در `api/production/openapi.yaml` قرار دارد.
