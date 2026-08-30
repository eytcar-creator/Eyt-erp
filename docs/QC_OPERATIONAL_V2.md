# E.Y.T QC & Traceability — Operational v2

## هدف
کنترل کیفیت آخرین سد قبل از ورود کالای تولیدشده به موجودی کالای قابل فروش است و برای هر بچ، سابقه کامل و قابل ممیزی ایجاد می‌کند.

## جریان عملیاتی
`Production Order → Quality Batch → Inspection → Pass/Fail → Finished Goods Release → Inventory → Sales`

## Batch
هر خروجی تولیدی که نیازمند کنترل کیفیت است با `batch_no` یکتا ثبت می‌شود و به `production_order_no` و `product_code` متصل است.

Batch شامل مقدار برنامه‌ریزی‌شده، مقدار پذیرفته‌شده، مقدار مردود و وضعیت چرخه عمر است.

## Inspection
نتیجه بازرسی یکی از `PASS`, `FAIL`, `CONDITIONAL` است. مقدار پذیرفته و مردود تجمعی نباید از مقدار برنامه‌ریزی‌شده بیشتر شود.

## Defect
نقص با کد، مقدار، شدت و شرح ثبت می‌شود. شدت‌ها: `MINOR`, `MAJOR`, `CRITICAL`.

## Release Safety
فقط Batch با وضعیت `PASSED` می‌تواند به Finished Goods Release برسد. پس از Release وضعیت Batch به `RELEASED` تغییر می‌کند.

Batchهای `FAILED` یا `BLOCKED` حق Release ندارند و نباید وارد موجودی قابل فروش شوند.

## Traceability
نقاط کلیدی زنجیره در `traceability_events` ثبت می‌شوند:
- ایجاد Batch
- عملیات تولید
- بازرسی QC
- قبولی/رد QC
- Release
- ارسال
- مرجوعی
- اسقاط

در صورت استفاده از Serial Number، شماره سریال نیز در رویداد نگهداری می‌شود.

## دسترسی
- `qc.read`: مشاهده QC و Traceability
- `qc.execute`: ایجاد Batch، بازرسی و رویدادهای Traceability
- `qc.release`: آزادسازی کالای نهایی

## API
- `POST /api/qc/batches`
- `GET /api/qc/batches/{batch_no}`
- `POST /api/qc/batches/{batch_no}/inspect`
- `POST /api/qc/batches/{batch_no}/release`
- `POST /api/qc/batches/{batch_no}/trace`
- `GET /api/qc/trace/{batch_no}`

## معیار پذیرش
1. Batch یکتا و قابل ردیابی باشد.
2. مقدار بازرسی از برنامه تولید عبور نکند.
3. Release فقط برای `PASSED` انجام شود.
4. Batch مردود/مسدود هرگز کالای قابل فروش نشود.
5. تاریخ، کاربر و مرجع رویداد قابل ممیزی باشد.
6. یک Batch بیش از یک Release نداشته باشد.
7. PostgreSQL E2E، ERP CI و Identity/RBAC CI قبل از Merge سبز باشند.
8. داده واقعی و اطلاعات مشتری داخل repository قرار نگیرد.
