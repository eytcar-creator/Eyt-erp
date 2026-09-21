# E.Y.T Firebase / Firestore Catalog Foundation

Project: eyt-catalog

## Purpose

Firestore is the public catalog/data-display layer for E.Y.T Catalog. It is not the operational ERP database.

Operational ERP remains FastAPI + PostgreSQL in this repository.

## Current catalog collection

eyt_catalog

Recommended document shape:

- model_id: stable vehicle/model identifier
- brand: vehicle brand/group
- model: model name
- year_from, year_to: optional applicability range
- category: product category
- products: catalog items for the model
- kits: kit definitions and included SKU references
- images: image URLs/paths
- updated_at: server timestamp
- version: schema/data version

Each product should ultimately carry:

- sku
- product_code
- name_fa
- name_en (optional)
- category
- vehicle_refs
- specifications
- images
- kit_refs
- active

## Security model

- Public catalog: client read-only.
- Client writes: denied.
- Sensitive operational data: denied from direct Firestore client access.
- Trusted backend/Admin SDK: responsible for controlled writes.
- Orders, customers, inventory, production, QC and finance stay behind the operational API.

## Migration note

The old Firebase Test Mode rule expired on 2026-09-04. Do not restore unrestricted read/write access.
