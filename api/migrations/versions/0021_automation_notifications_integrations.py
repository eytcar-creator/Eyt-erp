"""E.Y.T ERP automation, notifications and integrations

Revision ID: 0021
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notification_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("title_template", sa.String(300)),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("channel IN ('SMS','EMAIL','WHATSAPP','IN_APP','WEBHOOK')", name="ck_notification_channel"),
    )
    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("template_id", UUID(as_uuid=True), sa.ForeignKey("notification_templates.id", ondelete="SET NULL")),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("recipient", sa.String(300), nullable=False),
        sa.Column("title", sa.String(300)),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="QUEUED"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("reference_type", sa.String(80)),
        sa.Column("reference_id", UUID(as_uuid=True)),
        sa.Column("error_message", sa.Text()),
        sa.CheckConstraint("channel IN ('SMS','EMAIL','WHATSAPP','IN_APP','WEBHOOK')", name="ck_notification_instance_channel"),
        sa.CheckConstraint("status IN ('QUEUED','PROCESSING','SENT','FAILED','CANCELLED')", name="ck_notification_status"),
    )
    op.create_table(
        "integration_connections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("name_fa", sa.String(200), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("integration_type", sa.String(30), nullable=False),
        sa.Column("base_url", sa.String(500)),
        sa.Column("config_json", sa.JSON()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("integration_type IN ('WEBHOOK','API','N8N','SMS','WHATSAPP','ECOMMERCE','ACCOUNTING')", name="ck_integration_type"),
    )
    op.create_table(
        "automation_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(100), nullable=False, unique=True),
        sa.Column("name_fa", sa.String(200), nullable=False),
        sa.Column("trigger_event", sa.String(120), nullable=False),
        sa.Column("condition_json", sa.JSON()),
        sa.Column("action_type", sa.String(40), nullable=False),
        sa.Column("action_config", sa.JSON()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.CheckConstraint("action_type IN ('NOTIFY','WEBHOOK','CREATE_TASK','CREATE_APPROVAL','UPDATE_STATUS','N8N')", name="ck_automation_action_type"),
    )
    op.create_table(
        "automation_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("rule_id", UUID(as_uuid=True), sa.ForeignKey("automation_rules.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("payload", sa.JSON()),
        sa.Column("status", sa.String(20), nullable=False, server_default="QUEUED"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("run_after", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.CheckConstraint("status IN ('QUEUED','RUNNING','COMPLETED','FAILED','DEAD')", name="ck_automation_job_status"),
        sa.CheckConstraint("attempt_count >= 0 AND max_attempts > 0", name="ck_automation_job_attempts"),
    )
    op.create_index("idx_notifications_status_schedule", "notifications", ["status", "scheduled_at"])
    op.create_index("idx_automation_rule_event_active", "automation_rules", ["trigger_event", "is_active", "priority"])
    op.create_index("idx_automation_job_status_run_after", "automation_jobs", ["status", "run_after"])


def downgrade():
    op.drop_index("idx_automation_job_status_run_after", table_name="automation_jobs")
    op.drop_index("idx_automation_rule_event_active", table_name="automation_rules")
    op.drop_index("idx_notifications_status_schedule", table_name="notifications")
    op.drop_table("automation_jobs")
    op.drop_table("automation_rules")
    op.drop_table("integration_connections")
    op.drop_table("notifications")
    op.drop_table("notification_templates")
