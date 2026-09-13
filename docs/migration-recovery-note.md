# Migration recovery 018-020

Migrations 018, 019 and 020 were restored from their last known canonical commits onto `fix/restore-migrations-018-020` because they are absent from `main`.

Migration 020 uses the idempotent customer price-list constraint form from commit `e6bd097cc84bc4ca14f9e1eb336bdd1481e7b057`.

The branch is intended for review before merge. No production database migration has been executed by this change.
