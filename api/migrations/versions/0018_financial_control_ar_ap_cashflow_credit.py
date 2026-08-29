"""E.Y.T ERP financial control, AR/AP, cash flow and customer credit

Revision ID: 0018
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0018"
down_revision = ("0017_identity", "0017_demand")
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("financial_accounts", sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("code", sa.String(60), nullable=False, unique=True), sa.Column("name_fa", sa.String(200), nullable=False), sa.Column("account_type", sa.String(30), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.CheckConstraint("account_type IN ('CASH','BANK','RECEIVABLE','PAYABLE','REVENUE','EXPENSE','ASSET','LIABILITY','EQUITY')", name="ck_financial_account_type"))
    op.create_table("customer_credit_profiles", sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("credit_limit", sa.Numeric(18, 4), nullable=False, server_default="0"), sa.Column("credit_used", sa.Numeric(18, 4), nullable=False, server_default="0"), sa.Column("payment_term_days", sa.Integer(), nullable=False, server_default="0"), sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"), sa.CheckConstraint("credit_limit >= 0 AND credit_used >= 0", name="ck_customer_credit_nonnegative"), sa.CheckConstraint("payment_term_days >= 0", name="ck_customer_payment_terms"), sa.CheckConstraint("status IN ('ACTIVE','HOLD','BLOCKED')", name="ck_customer_credit_status"))
    op.create_table("receivables", sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("receivable_no", sa.String(80), nullable=False, unique=True), sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False), sa.Column("invoice_id", UUID(as_uuid=True), sa.ForeignKey("invoices.id", ondelete="SET NULL")), sa.Column("issue_date", sa.Date(), nullable=False, server_default=sa.func.current_date()), sa.Column("due_date", sa.Date()), sa.Column("original_amount", sa.Numeric(18, 4), nullable=False), sa.Column("paid_amount", sa.Numeric(18, 4), nullable=False, server_default="0"), sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"), sa.Column("notes", sa.Text()), sa.CheckConstraint("original_amount >= 0 AND paid_amount >= 0 AND paid_amount <= original_amount", name="ck_receivable_amounts"), sa.CheckConstraint("due_date IS NULL OR due_date >= issue_date", name="ck_receivable_dates"), sa.CheckConstraint("status IN ('OPEN','PARTIAL','PAID','OVERDUE','WRITTEN_OFF','CANCELLED')", name="ck_receivable_status"))
    op.create_table("payables", sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("payable_no", sa.String(80), nullable=False, unique=True), sa.Column("supplier_id", UUID(as_uuid=True), sa.ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False), sa.Column("purchase_order_id", UUID(as_uuid=True), sa.ForeignKey("purchase_orders.id", ondelete="SET NULL")), sa.Column("issue_date", sa.Date(), nullable=False, server_default=sa.func.current_date()), sa.Column("due_date", sa.Date()), sa.Column("original_amount", sa.Numeric(18, 4), nullable=False), sa.Column("paid_amount", sa.Numeric(18, 4), nullable=False, server_default="0"), sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"), sa.Column("notes", sa.Text()), sa.CheckConstraint("original_amount >= 0 AND paid_amount >= 0 AND paid_amount <= original_amount", name="ck_payable_amounts"), sa.CheckConstraint("due_date IS NULL OR due_date >= issue_date", name="ck_payable_dates"), sa.CheckConstraint("status IN ('OPEN','PARTIAL','PAID','OVERDUE','DISPUTED','CANCELLED')", name="ck_payable_status"))
    op.create_table("cash_transactions", sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("transaction_no", sa.String(80), nullable=False, unique=True), sa.Column("financial_account_id", UUID(as_uuid=True), sa.ForeignKey("financial_accounts.id", ondelete="RESTRICT"), nullable=False), sa.Column("transaction_type", sa.String(10), nullable=False), sa.Column("amount", sa.Numeric(18, 4), nullable=False), sa.Column("transaction_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("reference_type", sa.String(50)), sa.Column("reference_id", UUID(as_uuid=True)), sa.Column("description", sa.Text()), sa.CheckConstraint("transaction_type IN ('IN','OUT')", name="ck_cash_transaction_type"), sa.CheckConstraint("amount > 0", name="ck_cash_transaction_positive"))
    op.create_table("cash_flow_forecasts", sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("forecast_date", sa.Date(), nullable=False), sa.Column("category", sa.String(40), nullable=False), sa.Column("direction", sa.String(10), nullable=False), sa.Column("expected_amount", sa.Numeric(18, 4), nullable=False), sa.Column("confidence", sa.Numeric(5, 2)), sa.Column("reference_type", sa.String(50)), sa.Column("reference_id", UUID(as_uuid=True)), sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"), sa.Column("notes", sa.Text()), sa.CheckConstraint("direction IN ('IN','OUT')", name="ck_cash_flow_direction"), sa.CheckConstraint("expected_amount >= 0", name="ck_cash_flow_amount"), sa.CheckConstraint("confidence IS NULL OR confidence BETWEEN 0 AND 100", name="ck_cash_flow_confidence"), sa.CheckConstraint("status IN ('OPEN','CONFIRMED','REALIZED','CANCELLED')", name="ck_cash_flow_status"))
    op.create_index("idx_receivables_customer_status_due", "receivables", ["customer_id", "status", "due_date"])
    op.create_index("idx_payables_supplier_status_due", "payables", ["supplier_id", "status", "due_date"])
    op.create_index("idx_cash_transactions_account_date", "cash_transactions", ["financial_account_id", "transaction_date"])
    op.create_index("idx_cash_flow_date_direction", "cash_flow_forecasts", ["forecast_date", "direction", "status"])


def downgrade():
    op.drop_index("idx_cash_flow_date_direction", table_name="cash_flow_forecasts")
    op.drop_index("idx_cash_transactions_account_date", table_name="cash_transactions")
    op.drop_index("idx_payables_supplier_status_due", table_name="payables")
    op.drop_index("idx_receivables_customer_status_due", table_name="receivables")
    op.drop_table("cash_flow_forecasts")
    op.drop_table("cash_transactions")
    op.drop_table("payables")
    op.drop_table("receivables")
    op.drop_table("customer_credit_profiles")
    op.drop_table("financial_accounts")
