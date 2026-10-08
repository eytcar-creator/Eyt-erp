# E.Y.T One — Unified Commerce & Order Platform

## تعریف پروژه
**E.Y.T One** لایه مرکزی سفارش‌گیری، فروش و اتصال کانال‌های E.Y.T است.

این پروژه از ابتدا فقط «ثبت سفارش» نیست. هدف، ساخت یک هسته واحد برای اتصال کانال‌های فروش به Customer Hub، Order Center و ERP است تا اطلاعات سفارش، مشتری، محصول، موجودی، تولید، مالی، ارسال و وصول در یک زنجیره قابل ردیابی حرکت کنند.

> **Current Module:** E.Y.T One — Order Center

## معماری نام‌گذاری
- **E.Y.T One** — پلتفرم مرکزی تجارت و سفارش
- **Channel Hub** — دریافت و مدیریت ورودی کانال‌ها
- **Customer Hub** — شناسایی و یکپارچه‌سازی مشتری
- **Order Center** — هسته سفارش‌گیری و چرخه سفارش
- **Sales Center** — فروش، قیمت، اعتبار و پیشنهاد
- **Production Link** — اتصال سفارش به تولید
- **Inventory Link** — موجودی، رزرو و تخصیص
- **Finance Link** — پرداخت، بدهی، اعتبار و تسویه
- **Tracking** — رهگیری وضعیت سفارش و تحویل

## هدف
تمام سفارش‌های B2B، نمایندگان، فروش حضوری، سایت و پیام‌رسان‌های متصل باید به یک Order Center مرکزی وارد شوند. کانال فقط منبع ورود است و مالک سفارش نیست.

## جریان
Channel -> Channel Hub -> Order Intake -> Customer/Product Resolution -> Validation -> Customer Confirmation -> Order Center -> ERP

## کانال‌ها
web, b2b, representative, sales_agent, phone, bale, whatsapp, instagram, other

## وضعیت سفارش
DRAFT -> PENDING_CONFIRMATION -> CONFIRMED -> ALLOCATED -> BACKORDER/PRODUCTION -> READY_TO_SHIP -> SHIPPED -> DELIVERED -> SETTLEMENT -> CLOSED

کنترلی: ON_HOLD, CANCELLED, RETURNED

## قرارداد Intake
ورودی استاندارد:
- channel
- externalMessageId
- idempotencyKey
- customerExternalId (optional)
- customerId (optional)
- text (optional)
- items[]: sku/productCode, quantity
- requestedDeliveryDate (optional)
- paymentMode (optional)
- metadata (optional)

خروجی:
- intakeId
- orderNo (nullable تا قبل از تبدیل)
- status
- customerMatch
- productMatches
- validationErrors
- nextAction

## قواعد کسب‌وکار
1. هر سفارش Order ID یکتا دارد.
2. channel و externalMessageId برای traceability ذخیره می‌شوند.
3. پیام دریافتی از کانال تا قبل از تأیید مشتری فقط پیشنهاد سفارش است.
4. رزرو موجودی و تعهد تولید فقط بعد از CONFIRMED انجام می‌شود.
5. قیمت، اعتبار مشتری، موجودی و موعد تحویل قبل از تأیید نهایی کنترل می‌شوند.
6. تغییرات سفارش append-only audit event تولید می‌کند.
7. سفارش بدون Customer ID، SKU معتبر، تعداد، مسئول و وضعیت نهایی قابل تأیید نیست.
8. idempotency از ثبت دوباره پیام/سفارش جلوگیری می‌کند.

## امنیت کانال
- webhook signature verification
- RBAC
- rate limiting
- audit log
- secrets فقط از environment/secret manager
- credential/token هرگز در git ذخیره نشود
- اتصال پیام‌رسان فقط از API/Webhook رسمی و مجاز

## اتصال به ERP
E.Y.T One باید با موجودی، اعتبار مشتری، مالی، تولید، QC، انبار، ارسال و وصول از طریق API داخلی ارتباط داشته باشد.

## فازهای اجرا
1. Order Center API و مدل داده
2. Webhook/Channel Gateway
3. اتصال سایت eytparts.ir
4. B2B و نمایندگان
5. Bale در صورت وجود API رسمی و مجاز
6. WhatsApp/Instagram در صورت وجود API رسمی و مجاز
7. notification/escalation worker
8. customer tracking endpoint

## اصل معماری
هیچ کانالی نباید منطق مستقل سفارش‌گیری خود را داشته باشد. همه کانال‌ها به قرارداد واحد Intake متصل می‌شوند.

## اصل توسعه
E.Y.T One باید به‌صورت ماژولار توسعه داده شود؛ اضافه شدن کانال جدید نباید باعث ایجاد منطق سفارش‌گیری جدید شود. کانال فقط Adapter است و Order Center منبع حقیقت سفارش است.
