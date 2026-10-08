# E.Y.T Management Operating System v1.0

## Purpose
The management model separates direction, system development, process ownership and execution.

## Core rule
- CEO designs and directs the system.
- Managers own processes and results.
- Engineers and capable specialists build and improve the system.
- Execution staff execute standardized work.
- ERP + AI + data provide control, traceability and KPI visibility.

## Operating chain
Market / Demand -> Order -> Planning -> Product Master -> Procurement -> Receiving -> Incoming QC -> Production -> In-process QC -> Final QC -> Warehouse -> B2B/B2C/Retail -> Order Center -> Picking/Packing -> Shipment -> Delivery -> Collection -> Accounting -> Real Profit -> CEO Dashboard -> corrective action.

## Current role ownership
| Position | Owner | Main output |
|---|---|---|
| CEO | Saeed Rezaei Talebkhan | Strategy, system design, resources, management control |
| Production / Tabriz | Hamid / Reza | Production execution and workshop output |
| QC | Masoud Farhangi | Independent quality release, NCR, quarantine |
| Isfahan Rubber | Ehsan Eslami | Rubber/bushing development and stable production |
| Plating | Mohsen | Plating process execution and batch handoff |
| Tehran Shop + Accounting | Nima | Retail operation and accounting execution |
| Digital Commerce | To be appointed | Click One, sites, channels, SMS, CRM, B2C |
| System & Development | To be appointed | ERP, AI, automation, data and KPI |

## Authority rules
1. No responsibility without authority.
2. No authority without accountability.
3. No process without measurable KPI.
4. No critical transaction controlled end-to-end by one person.
5. QC is independent from production release.
6. Digital channels do not change Product Master, base price, inventory truth or finance directly.
7. Payments require request, approval, funding source, payment evidence and accounting registration.
8. Production cannot release nonconforming product to saleable inventory.

## CEO dashboard
Cash available, collections, overdue receivables, planned payments, sales, realized profit, production attainment, downtime, scrap, QC rejection/NCR, stock shortages, open orders, B2B/B2C performance and critical alerts.

## ERP implementation
The organizational model is represented in:
- org_positions
- org_kpis
- org_employee_assignments
- org_sod_rules

Migration: 0023_management_operating_model.py

Personnel assignment is intentionally not hard-coded into the migration because user UUIDs must come from the identity system.
