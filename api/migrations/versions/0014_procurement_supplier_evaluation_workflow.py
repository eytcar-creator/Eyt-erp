"""E.Y.T ERP procurement, supplier evaluation and purchase workflow

Revision ID: 0014
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("purchase_requests", sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("request_no", sa.String(80), nullable=False, unique=True), sa.Column("requested_by", sa.String(120)), sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT")), sa.Column("status", sa.String(25), nullable=False, server_default="DRAFT"), sa.Column("required_date", sa.Date()), sa.Column("notes", sa.Text()), sa.CheckConstraint("status IN ('DRAFT','SUBMITTED','APPROVED','REJECTED','ORDERED','CANCELLED')", name="ck_purchase_request_status"))
    op.create_table("purchase_request_items", sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("request_id", UUID(as_uuid=True), sa.ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False), sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False), sa.Column("quantity", sa.Numeric(18,6), nullable=False), sa.Column("notes", sa.Text()), sa.CheckConstraint("quantity > 0", name="ck_purchase_request_item_positive"))
    op.add_column("purchase_orders", sa.Column("request_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_purchase_orders_request_id", "purchase_orders", "purchase_requests", ["request_id"], ["id"], ondelete="SET NULL")
    op.create_table("supplier_evaluations", sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("supplier_id", UUID(as_uuid=True), sa.ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False), sa.Column("purchase_order_id", UUID(as_uuid=True), sa.ForeignKey("purchase_orders.id", ondelete="SET NULL")), sa.Column("quality_score", sa.Numeric(5,2), nullable=False, server_default="0"), sa.Column("delivery_score", sa.Numeric(5,2), nullable=False, server_default="0"), sa.Column("price_score", sa.Numeric(5,2), nullable=False, server_default="0"), sa.Column("service_score", sa.Numeric(5,2), nullable=False, server_default="0"), sa.Column("overall_score", sa.Numeric(5,2), nullable=False, server_default="0"), sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("notes", sa.Text()), sa.CheckConstraint("quality_score BETWEEN 0 AND 100 AND delivery_score BETWEEN 0 AND 100 AND price_score BETWEEN 0 AND 100 AND service_score BETWEEN 0 AND 100 AND overall_score BETWEEN 0 AND 100", name="ck_supplier_scores"))
    op.create_index("idx_purchase_requests_status_date", "purchase_requests", ["status", "required_date"])
    op.create_index("idx_purchase_orders_supplier_status", "purchase_orders", ["supplier_id", "status"])
    op.create_index("idx_purchase_orders_request", "purchase_orders", ["request_id"])
    op.create_index("idx_purchase_items_product", "purchase_order_items", ["product_id"])
    op.create_index("idx_supplier_eval_supplier_date", "supplier_evaluations", ["supplier_id", "evaluated_at"])

def downgrade():
    op.drop_index("idx_supplier_eval_supplier_date", table_name="supplier_evaluations")
    op.drop_index("idx_purchase_items_product", table_name="purchase_order_items")
    op.drop_index("idx_purchase_orders_request", table_name="purchase_orders")
    op.drop_index("idx_purchase_orders_supplier_status", table_name="purchase_orders")
    op.drop_index("idx_purchase_requests_status_date", table_name="purchase_requests")
    op.drop_table("supplier_evaluations")
    op.drop_constraint("fk_purchase_orders_request_id", "purchase_orders", type_="foreignkey")
    op.drop_column("purchase_orders", "request_id")
    op.drop_table("purchase_request_items")
    op.drop_table("purchase_requests")
