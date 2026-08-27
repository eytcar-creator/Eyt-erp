"""E.Y.T ERP finance, payments, receivables and accounting ledger

Revision ID: 0007
Reversible financial foundation linked to sales invoices and customers.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financial_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("account_code", sa.String(50), nullable=False, unique=True),
        sa.Column("name_fa", sa.String(200), nullable=False),
        sa.Column("account_type", sa.String(30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("account_type IN ('CASH','BANK','RECEIVABLE','PAYABLE','REVENUE','EXPENSE','INVENTORY','EQUITY','OTHER')", name="ck_fin_account_type"),
    )
    op.create_table(
        "payments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("payment_no", sa.String(80), nullable=False, unique=True),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="RESTRICT")),
        sa.Column("supplier_id", UUID(as_uuid=True), sa.ForeignKey("suppliers.id", ondelete="RESTRICT")),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("financial_accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("payment_type", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="IRR"),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("reference_no", sa.String(100)),
        sa.Column("status", sa.String(20), nullable=False, server_default="POSTED"),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("amount > 0", name="ck_payment_positive"),
        sa.CheckConstraint("payment_type IN ('RECEIPT','DISBURSEMENT')", name="ck_payment_type"),
        sa.CheckConstraint("status IN ('DRAFT','POSTED','VOID')", name="ck_payment_status"),
        sa.CheckConstraint("NOT (customer_id IS NOT NULL AND supplier_id IS NOT NULL)", name="ck_payment_party_exclusive"),
    )
    op.create_table(
        "receivable_allocations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("payment_id", UUID(as_uuid=True), sa.ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("invoice_id", UUID(as_uuid=True), sa.ForeignKey("sales_invoices.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("allocated_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("allocated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("allocated_amount > 0", name="ck_allocation_positive"),
        sa.UniqueConstraint("payment_id", "invoice_id", name="uq_payment_invoice_allocation"),
    )
    op.create_table(
        "accounting_journal_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("journal_no", sa.String(80), nullable=False, unique=True),
        sa.Column("entry_date", sa.Date(), nullable=False, server_default=sa.func.current_date()),
        sa.Column("reference_type", sa.String(50)),
        sa.Column("reference_id", UUID(as_uuid=True)),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(20), nullable=False, server_default="POSTED"),
        sa.CheckConstraint("status IN ('DRAFT','POSTED','VOID')", name="ck_journal_status"),
    )
    op.create_table(
        "accounting_journal_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("journal_entry_id", UUID(as_uuid=True), sa.ForeignKey("accounting_journal_entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("financial_accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("debit", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("credit", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("description", sa.Text()),
        sa.CheckConstraint("debit >= 0 AND credit >= 0", name="ck_journal_line_nonnegative"),
        sa.CheckConstraint("NOT (debit > 0 AND credit > 0)", name="ck_journal_line_one_side"),
        sa.CheckConstraint("debit > 0 OR credit > 0", name="ck_journal_line_nonzero"),
    )
    op.create_index("idx_payments_customer_date", "payments", ["customer_id", "paid_at"])
    op.create_index("idx_payments_supplier_date", "payments", ["supplier_id", "paid_at"])
    op.create_index("idx_receivable_invoice", "receivable_allocations", ["invoice_id"])
    op.create_index("idx_journal_reference", "accounting_journal_entries", ["reference_type", "reference_id"])


def downgrade():
    op.drop_index("idx_journal_reference", table_name="accounting_journal_entries")
    op.drop_index("idx_receivable_invoice", table_name="receivable_allocations")
    op.drop_index("idx_payments_supplier_date", table_name="payments")
    op.drop_index("idx_payments_customer_date", table_name="payments")
    op.drop_table("accounting_journal_lines")
    op.drop_table("accounting_journal_entries")
    op.drop_table("receivable_allocations")
    op.drop_table("payments")
    op.drop_table("financial_accounts")
