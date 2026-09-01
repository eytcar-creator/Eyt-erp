# E.Y.T Catalog Live Integration

این پرتال باید سفارش واقعی را از طریق Order Center ثبت و پیگیری کند؛ localStorage فقط fallback آفلاین/دمو است.

## API

Base: `/api/v1`

### ثبت سفارش
`POST /orders`

```json
{
  "customer_id": "CUSTOMER-UUID",
  "warehouse_code": "MAIN",
  "channel": "WEBSITE",
  "notes": "...",
  "items": [
    {"product_id": "PRODUCT-UUID", "quantity": 100, "unit_price": 0}
  ]
}
```

هدر `Idempotency-Key` برای جلوگیری از ثبت تکراری سفارش استفاده شود.

### پیگیری
`GET /orders/{orderNo}`

وضعیت‌های Order Center:
`DRAFT → PENDING_CONFIRMATION → CONFIRMED → RESERVED → PREPARING → READY_TO_SHIP → SHIPPED → DELIVERED`

وضعیت‌های `CANCELLED` و `RETURNED` باید به‌عنوان وضعیت استثنایی نمایش داده شوند.

## اصل Master Data

Portal نباید SKU یا Product UUID را خودش تولید کند. Product Master ERP مرجع یکتا است. مشتری نیز باید پس از احراز هویت، `customer_id` معتبر ERP داشته باشد.

## اتصال به تولید

پس از تأیید سفارش، Order Center باید سفارش را به گردش تولید موجود E.Y.T متصل کند. قرارداد تولید در `api/production/openapi.yaml` شامل ایجاد Production Order، شروع/اتمام عملیات و ثبت QC است.

## استقرار

- Frontend: `eyt-catalog.ir`
- API: مسیر `/api/v1`
- Database: PostgreSQL مرکزی ERP
- HTTPS الزامی
- CORS فقط برای دامنه‌های رسمی E.Y.T

## معیار تکمیل v1

1. مشتری احراز هویت شود.
2. محصول از Product Master انتخاب شود.
3. سفارش در PostgreSQL ایجاد شود.
4. E.Y.T سفارش را در Order Center ببیند.
5. تأیید سفارش رزرو موجودی را انجام دهد.
6. سفارش تولید/عملیات تولید قابل پیگیری باشد.
7. QC ثبت شود.
8. مشتری وضعیت سفارش را آنلاین ببیند.
