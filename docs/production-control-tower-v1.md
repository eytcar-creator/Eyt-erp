# E.Y.T Production Control Tower v1

## هدف

کنترل هم‌زمان چند سفارش تولید در چند کارگاه و چند عملیات، با ردیابی WIP، انتقال بین محل‌ها، ظرفیت، تأخیر، ضایعات، هزینه و اثر نقدینگی.

## اصل داده

هر Production Order یک شناسه یکتا دارد و هر عملیات یک Operation شناسه‌دار دارد. موجودی در جریان ساخت (WIP) فقط از طریق رویدادهای ثبت‌شده جابه‌جا می‌شود. هیچ مقدار دستی نباید وضعیت مرحله بعد را تغییر دهد.

## وضعیت‌های استاندارد عملیات

`planned` → `queued` → `in_progress` → `completed` → `qc_hold` → `released`

حالت‌های استثنایی:

`blocked`، `delayed`، `rework`، `scrapped`، `cancelled`

## اطلاعات اجباری هر Operation

- production_order_no
- sequence_no
- operation_code / operation_name
- work_center / workshop
- responsible_person یا contractor
- planned_start / planned_end
- actual_start / actual_end
- input_qty
- accepted_qty
- rejected_qty
- waste_qty
- service_cost
- transport_cost
- queue_time
- process_time
- waiting_time
- downtime
- rework_qty
- source_location / destination_location

قاعده مقدارها: `accepted + rejected + waste = input` مگر اینکه رویداد رسمی انتقال/تغییر مقدار ثبت شده باشد.

## Control Tower

نمای اصلی باید برای تمام سفارش‌های باز این ستون‌ها را ارائه کند:

| فیلد | معنی |
|---|---|
| Order | شماره سفارش تولید |
| Product | محصول و SKU |
| Target | مقدار هدف |
| Current Operation | آخرین عملیات فعال |
| Location | کارگاه/انبار فعلی |
| WIP Qty | مقدار در جریان ساخت |
| Accepted | مقدار سالم |
| Scrap | ضایعات تجمعی |
| Planned End | موعد مرحله |
| Delay | تأخیر به روز/ساعت |
| Queue | زمان صف |
| Process | زمان واقعی فرآیند |
| Cost | هزینه واقعی تجمعی |
| Status | وضعیت عملیاتی |

## هشدارها

- `MATERIAL_SHORTAGE`: مواد کافی برای ادامه تولید نیست.
- `OPERATION_OVERDUE`: موعد عملیات گذشته است.
- `WIP_STUCK`: WIP بیش از آستانه مجاز در یک محل مانده است.
- `CAPACITY_CONSTRAINT`: ظرفیت مرکز کاری برای برنامه کافی نیست.
- `EXTERNAL_PROCESS_OVERDUE`: عملیات پیمانکاری از موعد برگشت گذشته است.
- `SCRAP_SPIKE`: نرخ ضایعات از حد مجاز محصول/عملیات بیشتر شده است.
- `QC_HOLD`: محصول تا تأیید QC قابل انتقال به Finished Goods نیست.
- `RECEIVABLE_RISK`: فروش انجام شده ولی وصول مطابق شرایط اعتباری عقب افتاده است.

## اتصال به انبار

هر شروع/پایان عملیات و هر انتقال بین کارگاه‌ها باید رویداد موجودی متناظر داشته باشد. Finished Goods فقط پس از QC نهایی موفق آزاد می‌شود.

مسیر نمونه:

`Raw Material → Workshop A → Workshop B → External Plating → Assembly → QC → Finished Goods`

## اتصال به فروش

Sales Order می‌تواند نیاز تولید ایجاد کند. موجودی قابل فروش از موجودی رزروشده و موجودی در WIP تفکیک می‌شود. تحویل فروش فقط از موجودی آزاد انجام می‌شود.

## اتصال به سود واقعی

برای هر Production Order باید این زنجیره قابل محاسبه باشد:

`Actual Production Cost + Scrap Cost + Holding Cost + Distribution/Sales Cost + Financing/Receivable Cost`

سپس:

`Collected Cash - True Cost = Real Cash Profit`

هزینه‌های سربار جذب‌شده نباید دوباره در مرحله دیگری ثبت شوند.

## Pilot: سیبک فرمان آریو

- Target: 2,000 عدد
- ماده اولیه: CK45، قطر 24، وزن استاندارد 0.9 kg/قطعه
- ظرفیت فورج: 400/day
- ظرفیت CNC: 350/day
- ظرفیت رزوه: 800/day
- ظرفیت آبکاری/رنگ: 700/day
- ظرفیت مونتاژ: 300/day
- QC: 1 day
- ضایعات اعلام‌شده: 4 عدد در هر یک از 5 مرحله = 20 عدد

این اعداد به‌عنوان Master Data واقعی Pilot استفاده می‌شوند و نباید به سایر محصولات تعمیم داده شوند.

## معیار پذیرش

1. مدیر بتواند وضعیت همه سفارش‌های باز را در یک صفحه ببیند.
2. برای هر سفارش، محل فعلی WIP مشخص باشد.
3. مقدار ورودی/سالم/ضایعات هر عملیات قابل ردیابی باشد.
4. تأخیر بر اساس planned vs actual محاسبه شود.
5. Queue Time از Process Time جدا باشد.
6. انتقال بین کارگاه‌ها با سند و موجودی ثبت شود.
7. QC ناموفق مانع آزادسازی Finished Goods شود.
8. هزینه واقعی سفارش با فروش و وصول قابل پیوند باشد.
9. هیچ داده آزمایشی بدون برچسب وارد محیط واقعی نشود.
