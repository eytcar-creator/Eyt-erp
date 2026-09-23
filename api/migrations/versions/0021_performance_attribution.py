"""Performance attribution fields for production execution.

Revision ID: 0021
"""

from alembic import op
import sqlalchemy as sa

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "production_operations",
        sa.Column("performed_by", sa.String(100), nullable=True),
    )
    op.create_index(
        "idx_production_operations_performed_by_end",
        "production_operations",
        ["performed_by", "actual_end"],
    )


def downgrade():
    op.drop_index(
        "idx_production_operations_performed_by_end",
        table_name="production_operations",
    )
    op.drop_column("production_operations", "performed_by")
