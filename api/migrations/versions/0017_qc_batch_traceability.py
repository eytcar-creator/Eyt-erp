"""E.Y.T ERP QC extension marker.

Revision ID: 0017
Revision chain: 0016 -> 0017

QC batch/release/traceability tables are part of the runnable SQL baseline
migration 007. The Alembic segment remains as a historical extension marker
for environments that track the 0015+ segment, but must not recreate tables
already supplied by the canonical operational baseline.
"""
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade():
    # Intentionally empty. Canonical QC schema is applied by SQL migration 007.
    pass


def downgrade():
    # Intentionally empty. SQL migration 007 owns the canonical schema.
    pass
