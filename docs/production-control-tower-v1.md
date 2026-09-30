# E.Y.T Production Control Tower v1

کنترل هم‌زمان سفارش‌های تولید در چند کارگاه و عملیات با داده واقعی PostgreSQL، ردیابی WIP، تأخیر، ضایعات، هزینه و اثر نقدینگی.

وضعیت: planned → queued → in_progress → completed → qc_hold → released
استثناها: blocked، delayed، rework، scrapped، cancelled

هشدارها: MATERIAL_SHORTAGE، OPERATION_OVERDUE، WIP_STUCK، CAPACITY_CONSTRAINT، EXTERNAL_PROCESS_OVERDUE، SCRAP_SPIKE، QC_HOLD، RECEIVABLE_RISK.

مسیر: Raw Material → Workshop → External Process → Assembly → QC → Finished Goods → Delivery → Invoice → Collection → Real Cash Profit.

معیار پذیرش: وضعیت سفارش‌های باز، محل WIP، مقدار سالم/ضایعات، تأخیر، زمان صف و فرآیند، انتقال بین کارگاه‌ها، QC و اتصال هزینه واقعی به فروش و وصول باید قابل ردیابی باشد.
