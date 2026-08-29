"""E.Y.T ERP roles, permissions, approvals and audit log

Revision ID: 0020
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("name_fa", sa.String(160), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(120), nullable=False, unique=True),
        sa.Column("module", sa.String(80), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("description", sa.Text()),
        sa.UniqueConstraint("module", "action", name="uq_permission_module_action"),
    )
    op.create_table(
        "role_permissions",
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", UUID(as_uuid=True), sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "approval_workflows",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("name_fa", sa.String(160), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "approval_steps",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workflow_id", UUID(as_uuid=True), sa.ForeignKey("approval_workflows.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_no", sa.Integer(), nullable=False),
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("min_amount", sa.Numeric(20, 4)),
        sa.Column("max_amount", sa.Numeric(20, 4)),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("workflow_id", "step_no", name="uq_approval_step_number"),
        sa.CheckConstraint("step_no > 0", name="ck_approval_step_positive"),
        sa.CheckConstraint("min_amount IS NULL OR max_amount IS NULL OR max_amount >= min_amount", name="ck_approval_step_amount_range"),
    )
    op.create_table(
        "approval_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workflow_id", UUID(as_uuid=True), sa.ForeignKey("approval_workflows.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("current_step_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('PENDING','APPROVED','REJECTED','CANCELLED')", name="ck_approval_request_status"),
    )
    op.create_table(
        "approval_actions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("approval_request_id", UUID(as_uuid=True), sa.ForeignKey("approval_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_no", sa.Integer(), nullable=False),
        sa.Column("acted_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("acted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("action IN ('APPROVE','REJECT','RETURN','CANCEL')", name="ck_approval_action"),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("actor_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("old_data", sa.JSON()),
        sa.Column("new_data", sa.JSON()),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_permission_module_action", "permissions", ["module", "action"])
    op.create_index("idx_approval_request_entity_status", "approval_requests", ["entity_type", "entity_id", "status"])
    op.create_index("idx_approval_action_request_step", "approval_actions", ["approval_request_id", "step_no"])
    op.create_index("idx_audit_entity_date", "audit_logs", ["entity_type", "entity_id", "created_at"])
    op.create_index("idx_audit_actor_date", "audit_logs", ["actor_user_id", "created_at"])


def downgrade():
    op.drop_index("idx_audit_actor_date", table_name="audit_logs")
    op.drop_index("idx_audit_entity_date", table_name="audit_logs")
    op.drop_index("idx_approval_action_request_step", table_name="approval_actions")
    op.drop_index("idx_approval_request_entity_status", table_name="approval_requests")
    op.drop_index("idx_permission_module_action", table_name="permissions")
    op.drop_table("audit_logs")
    op.drop_table("approval_actions")
    op.drop_table("approval_requests")
    op.drop_table("approval_steps")
    op.drop_table("approval_workflows")
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
