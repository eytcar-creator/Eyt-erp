# E.Y.T IDEA ENGINE

**اصل:** هر چیزی که عادی شده، یک بار باید دوباره طراحی شود.

Observation -> Idea -> Screening -> Evaluation -> Prototype -> Pilot -> Standardize -> Realized

هر ایده مسئله، فرآیند فعلی، راه‌حل پیشنهادی، مالک، امتیازهای ارزیابی، ارزش مالی/زمانی، هزینه اجرا و نتیجه واقعی را ثبت می‌کند.

Priority = 20% customer value + 25% financial impact + 20% feasibility + 20% strategic fit + 10% (100-effort) + 5% (100-risk).

API:
- POST /api/v1/innovation/ideas
- GET /api/v1/innovation/ideas
- GET /api/v1/innovation/ideas/{id}
- PATCH /api/v1/innovation/ideas/{id}
- POST /api/v1/innovation/ideas/{id}/score
- POST /api/v1/innovation/ideas/{id}/advance
- POST /api/v1/innovation/ideas/{id}/realize
- GET /api/v1/innovation/dashboard

Permissions: innovation.submit, innovation.manage.
