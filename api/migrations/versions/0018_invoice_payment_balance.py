"""Allow invoice receivables to decrease as payments are allocated.

Revision ID: 0018
Revision chain: 0017 -> 0018

The invoice baseline historically constrained receivable_amount to remain
exactly equal to subtotal minus prepayment. That is valid at issuance but
invalid after a payment reduces the outstanding balance. This revision keeps
the invariant bounded and non-negative while allowing normal payment flow.
"""
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE invoices DROP CONSTRAINT IF EXISTS invoices_check1")
    op.execute(
        """ALTER TABLE invoices
           ADD CONSTRAINT invoices_receivable_balance_check
           CHECK (
               receivable_amount >= 0
               AND receivable_amount <= subtotal - prepayment_amount
           )"""
    )


def downgrade():
    op.execute("ALTER TABLE invoices DROP CONSTRAINT IF EXISTS invoices_receivable_balance_check")
    op.execute(
        """ALTER TABLE invoices
           ADD CONSTRAINT invoices_check1
           CHECK (receivable_amount = subtotal - prepayment_amount)"""
    )
