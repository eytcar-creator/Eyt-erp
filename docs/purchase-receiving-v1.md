# E.Y.T ERP Purchase & Receiving v1

1. هر خط خرید به Product Master UUID متصل است.
2. Purchase Order موجودی را افزایش نمی‌دهد.
3. فقط Receipt تأییدشده موجودی را افزایش می‌دهد.
4. دریافت بیش از سفارش فقط با سیاست مجاز است.
5. هر Receipt تراکنش موجودی با warehouse، quantity، unit cost و source document می‌سازد.
6. خرید و دریافت نیازمند احراز هویت و audit هستند.
7. دریافت ناقص مجاز است.
8. وضعیت: draft → approved → partially_received → received.
9. سفارش لغوشده قابل دریافت نیست.
10. مبالغ با Decimal و rounding قطعی ثبت می‌شوند.

Supplier → Purchase Order → Approval → Partial/Full Receipt → Inventory → Audit → Final Receipt → Payable
