"""E.Y.T ERP CRM contacts, pipeline and follow-ups

Revision ID: 0011
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "customer_contacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("job_title", sa.String(120)),
        sa.Column("mobile", sa.String(40)),
        sa.Column("phone", sa.String(40)),
        sa.Column("email", sa.String(200)),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "crm_opportunities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("opportunity_no", sa.String(80), nullable=False, unique=True),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("contact_id", UUID(as_uuid=True), sa.ForeignKey("customer_contacts.id", ondelete="SET NULL")),
        sa.Column("title", sa.String(250), nullable=False),
        sa.Column("stage", sa.String(30), nullable=False, server_default="LEAD"),
        sa.Column("probability", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("estimated_value", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("expected_close_date", sa.Date()),
        sa.Column("source", sa.String(60)),
        sa.Column("owner", sa.String(120)),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("probability BETWEEN 0 AND 100", name="ck_crm_probability"),
        sa.CheckConstraint("estimated_value >= 0", name="ck_crm_estimated_value"),
        sa.CheckConstraint("stage IN ('LEAD','QUALIFIED','PROPOSAL','NEGOTIATION','WON','LOST')", name="ck_crm_stage"),
    )
    op.create_table(
        "crm_activities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("opportunity_id", UUID(as_uuid=True), sa.ForeignKey("crm_opportunities.id", ondelete="CASCADE")),
        sa.Column("contact_id", UUID(as_uuid=True), sa.ForeignKey("customer_contacts.id", ondelete="SET NULL")),
        sa.Column("activity_type", sa.String(30), nullable=False),
        sa.Column("subject", sa.String(250), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("activity_type IN ('CALL','WHATSAPP','SMS','EMAIL','MEETING','VISIT','TASK','OTHER')", name="ck_crm_activity_type"),
        sa.CheckConstraint("status IN ('OPEN','DONE','CANCELLED')", name="ck_crm_activity_status"),
    )
    op.create_table(
        "crm_followups",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("opportunity_id", UUID(as_uuid=True), sa.ForeignKey("crm_opportunities.id", ondelete="CASCADE")),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="NORMAL"),
        sa.Column("assigned_to", sa.String(120)),
        sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("priority IN ('LOW','NORMAL','HIGH','URGENT')", name="ck_crm_followup_priority"),
        sa.CheckConstraint("status IN ('OPEN','DONE','CANCELLED')", name="ck_crm_followup_status"),
    )
    op.create_index("idx_contacts_customer", "customer_contacts", ["customer_id"])
    op.create_index("idx_opportunities_customer_stage", "crm_opportunities", ["customer_id", "stage"])
    op.create_index("idx_activities_scheduled", "crm_activities", ["status", "scheduled_at"])
    op.create_index("idx_followups_due", "crm_followups", ["status", "due_at"])


def downgrade():
    op.drop_index("idx_followups_due", table_name="crm_followups")
    op.drop_index("idx_activities_scheduled", table_name="crm_activities")
    op.drop_index("idx_opportunities_customer_stage", table_name="crm_opportunities")
    op.drop_index("idx_contacts_customer", table_name="customer_contacts")
    op.drop_table("crm_followups")
    op.drop_table("crm_activities")
    op.drop_table("crm_opportunities")
    op.drop_table("customer_contacts")
