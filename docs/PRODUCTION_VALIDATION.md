# Production validation

این workflow قبل از هر استقرار واقعی، کد E.Y.T را بررسی می‌کند:
- نصب dependencyها
- compile شدن Python
- اجرای تست‌ها
- اعتبارسنجی Docker Compose
- build شدن image بک‌اند
- build شدن image کاتالوگ

این مرحله عمداً deploy خودکار ندارد؛ تا زمانی که مقصد واقعی استقرار، secrets و DNS مشخص و قابل کنترل نباشد، CI نباید چیزی را روی اینترنت منتشر کند.
