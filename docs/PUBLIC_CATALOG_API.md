# E.Y.T Public Catalog API

The public catalog is a read-only projection of the canonical PostgreSQL Product Master.

Operational ERP data remains in FastAPI + PostgreSQL. Firestore is optional cache/display
infrastructure and is not the source of truth for inventory, production, purchasing, finance,
or customer records.

Endpoints:
- GET /api/public/catalog/products
- GET /api/public/catalog/products/{sku}

Filters:
- q: SKU, Code128, Persian/English product name
- make: vehicle make
- model: vehicle model
- limit: 1..200

The response excludes internal production cost, supplier, margin, and purchasing fields.

Data flow:
Product Master -> Public Catalog API -> eyt-catalog.ir
Optional controlled cache:
Product Master -> server-side sync -> Firestore eyt_catalog -> public clients

Sync credentials must never be placed in the browser or committed to Git.
