# E.Y.T ERP — Execution Roadmap

## هدف
تبدیل E.Y.T ERP به یک سیستم عملیاتی یکپارچه برای محصول، خرید، انبار، تولید، کیفیت، فروش و مالی.

## وضعیت فعلی
- FastAPI backend فعال
- احراز هویت و RBAC
- JWT rotation/revocation
- Audit logging
- Product Master و جستجوی محصول
- Inventory balance/transactions
- Dashboard API
- Procurement / production / costing / sales / finance routers
- Health و readiness endpoints

## ترتیب اجرای باقی‌مانده
1. تثبیت Database migrations و اجرای migration chain از ابتدا تا head
2. تست integration برای auth، products، inventory و procurement
3. تکمیل Master Catalog قطعات E.Y.T
4. اتصال BOM به Production Order و مصرف مواد
5. ثبت عملیات پیمانکاری: آهن، فورج، CNC، رزوه، آبکاری و مونتاژ
6. محاسبه بهای تمام‌شده شامل مواد، اجرت، پیمانکار و زمان خواب مواد
7. کنترل کیفیت و ردیابی بچ/سری ساخت
8. اتصال فروش، تحویل، فاکتور و حساب مشتری
9. اتصال مالی و دریافت/پرداخت
10. اتصال n8n برای گردش‌های خودکار و اعلان‌ها
11. آماده‌سازی Odoo import/export
12. Docker production deployment و backup/restore test

## قواعد داده E.Y.T
- سیبک‌ها: سیبک فرمان و سیبک طبق
- بوش‌ها: خانواده جلوبندی/تعلیق
- سه‌شاخ: در سبد قطعات E.Y.T نیست و نباید در Category Tree یا Master Catalog درج شود.
- Product UUID باید برای هر محصول پایدار باشد.
- Kit و Pack باید اجزا و امکان فروش تکی را نگهداری کنند.

## معیار پایان MVP
یک سفارش واقعی باید از ثبت مشتری و محصول، کنترل موجودی، خرید/تولید، کنترل کیفیت، خروج کالا، فروش و ثبت مالی تا گزارش سود قابل ردیابی باشد.
