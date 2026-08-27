"""E.Y.T ERP vehicle catalog, fitment and OEM cross-reference

Revision ID: 0008
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vehicle_makes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("country", sa.String(100)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "vehicle_models",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("make_id", UUID(as_uuid=True), sa.ForeignKey("vehicle_makes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("model_code", sa.String(80)),
        sa.Column("year_from", sa.SmallInteger()),
        sa.Column("year_to", sa.SmallInteger()),
        sa.Column("engine", sa.String(120)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("make_id", "name", "model_code", name="uq_vehicle_model_identity"),
    )
    op.create_table(
        "vehicle_fitments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("vehicle_model_id", UUID(as_uuid=True), sa.ForeignKey("vehicle_models.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("position", sa.String(50)),
        sa.Column("side", sa.String(20)),
        sa.Column("notes", sa.Text()),
        sa.UniqueConstraint("product_id", "vehicle_model_id", "position", "side", name="uq_vehicle_fitment"),
    )
    op.create_table(
        "oem_cross_references",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("oem_brand", sa.String(120), nullable=False),
        sa.Column("oem_part_no", sa.String(120), nullable=False),
        sa.Column("reference_type", sa.String(30), nullable=False, server_default="OEM"),
        sa.Column("notes", sa.Text()),
        sa.UniqueConstraint("oem_brand", "oem_part_no", name="uq_oem_brand_part"),
        sa.CheckConstraint("reference_type IN ('OEM','AFTERMARKET','CROSS')", name="ck_oem_reference_type"),
    )
    op.create_table(
        "eyt_product_mappings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("fitment_id", UUID(as_uuid=True), sa.ForeignKey("vehicle_fitments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("mapping_role", sa.String(30), nullable=False, server_default="PRIMARY"),
        sa.Column("confidence", sa.Numeric(5, 2), nullable=False, server_default="100"),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint("confidence BETWEEN 0 AND 100", name="ck_mapping_confidence"),
        sa.CheckConstraint("mapping_role IN ('PRIMARY','ALTERNATIVE','KIT_COMPONENT')", name="ck_mapping_role"),
        sa.UniqueConstraint("product_id", "fitment_id", name="uq_eyt_product_fitment"),
    )
    op.create_index("idx_vehicle_models_make", "vehicle_models", ["make_id"])
    op.create_index("idx_fitments_vehicle", "vehicle_fitments", ["vehicle_model_id"])
    op.create_index("idx_fitments_product", "vehicle_fitments", ["product_id"])
    op.create_index("idx_oem_product", "oem_cross_references", ["product_id"])


def downgrade():
    op.drop_index("idx_oem_product", table_name="oem_cross_references")
    op.drop_index("idx_fitments_product", table_name="vehicle_fitments")
    op.drop_index("idx_fitments_vehicle", table_name="vehicle_fitments")
    op.drop_index("idx_vehicle_models_make", table_name="vehicle_models")
    op.drop_table("eyt_product_mappings")
    op.drop_table("oem_cross_references")
    op.drop_table("vehicle_fitments")
    op.drop_table("vehicle_models")
    op.drop_table("vehicle_makes")
