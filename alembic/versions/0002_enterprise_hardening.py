"""enterprise hardening schema"""

from __future__ import annotations

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "0002_enterprise_hardening"
down_revision = "0002_report_job_workflow_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    now = datetime.now(timezone.utc)

    op.create_table(
        "organizations",
        sa.Column("organization_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(length=96), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)
    op.create_index("ix_organizations_name", "organizations", ["name"], unique=True)
    op.create_index("ix_organizations_status", "organizations", ["status"], unique=False)

    organizations = sa.table(
        "organizations",
        sa.column("organization_id", sa.Integer()),
        sa.column("slug", sa.String()),
        sa.column("name", sa.String()),
        sa.column("status", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        organizations,
        [
            {
                "organization_id": 1,
                "slug": "healthsphere-medical",
                "name": "HealthSphere Medical",
                "status": "active",
                "created_at": now,
                "updated_at": now,
            }
        ],
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_users_organization_id", ["organization_id"], unique=False)
        batch_op.create_foreign_key("fk_users_organization_id", "organizations", ["organization_id"], ["organization_id"])

    with op.batch_alter_table("patients") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_patients_organization_id", ["organization_id"], unique=False)
        batch_op.create_foreign_key("fk_patients_organization_id", "organizations", ["organization_id"], ["organization_id"])

    with op.batch_alter_table("alerts") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_alerts_organization_id", ["organization_id"], unique=False)
        batch_op.create_foreign_key("fk_alerts_organization_id", "organizations", ["organization_id"], ["organization_id"])

    with op.batch_alter_table("report_jobs") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=128), nullable=True))
        batch_op.create_index("ix_report_jobs_organization_id", ["organization_id"], unique=False)
        batch_op.create_index("ix_report_jobs_idempotency_key", ["idempotency_key"], unique=False)
        batch_op.create_foreign_key("fk_report_jobs_organization_id", "organizations", ["organization_id"], ["organization_id"])

    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_audit_logs_organization_id", ["organization_id"], unique=False)
        batch_op.create_foreign_key("fk_audit_logs_organization_id", "organizations", ["organization_id"], ["organization_id"])

    with op.batch_alter_table("notifications") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_notifications_organization_id", ["organization_id"], unique=False)
        batch_op.create_foreign_key("fk_notifications_organization_id", "organizations", ["organization_id"], ["organization_id"])

    with op.batch_alter_table("imaging_studies") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_imaging_studies_organization_id", ["organization_id"], unique=False)
        batch_op.create_foreign_key("fk_imaging_studies_organization_id", "organizations", ["organization_id"], ["organization_id"])

    op.execute("UPDATE users SET organization_id = 1 WHERE organization_id IS NULL")
    op.execute("UPDATE patients SET organization_id = 1 WHERE organization_id IS NULL")
    op.execute("UPDATE alerts SET organization_id = 1 WHERE organization_id IS NULL")
    op.execute("UPDATE report_jobs SET organization_id = 1 WHERE organization_id IS NULL")
    op.execute("UPDATE notifications SET organization_id = 1 WHERE organization_id IS NULL")
    op.execute("UPDATE imaging_studies SET organization_id = 1 WHERE organization_id IS NULL")

    op.create_table(
        "user_sessions",
        sa.Column("session_id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=128), nullable=False),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("refresh_token_hash"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"], unique=False)
    op.create_index("ix_user_sessions_refresh_token_hash", "user_sessions", ["refresh_token_hash"], unique=True)
    op.create_index("ix_user_sessions_created_at", "user_sessions", ["created_at"], unique=False)
    op.create_index("ix_user_sessions_last_used_at", "user_sessions", ["last_used_at"], unique=False)
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"], unique=False)
    op.create_index("ix_user_sessions_revoked_at", "user_sessions", ["revoked_at"], unique=False)

    op.create_table(
        "invite_codes",
        sa.Column("invite_id", sa.String(length=64), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.organization_id"), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("created_by_username", sa.String(length=64), sa.ForeignKey("users.username"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("code_hash"),
    )
    op.create_index("ix_invite_codes_organization_id", "invite_codes", ["organization_id"], unique=False)
    op.create_index("ix_invite_codes_role", "invite_codes", ["role"], unique=False)
    op.create_index("ix_invite_codes_email", "invite_codes", ["email"], unique=False)
    op.create_index("ix_invite_codes_code_hash", "invite_codes", ["code_hash"], unique=True)
    op.create_index("ix_invite_codes_status", "invite_codes", ["status"], unique=False)
    op.create_index("ix_invite_codes_created_at", "invite_codes", ["created_at"], unique=False)
    op.create_index("ix_invite_codes_expires_at", "invite_codes", ["expires_at"], unique=False)

    op.create_table(
        "care_tasks",
        sa.Column("task_id", sa.String(length=64), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.organization_id"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.patient_id"), nullable=False),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("assignee_username", sa.String(length=64), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_care_tasks_organization_id", "care_tasks", ["organization_id"], unique=False)
    op.create_index("ix_care_tasks_patient_id", "care_tasks", ["patient_id"], unique=False)
    op.create_index("ix_care_tasks_status", "care_tasks", ["status"], unique=False)
    op.create_index("ix_care_tasks_priority", "care_tasks", ["priority"], unique=False)
    op.create_index("ix_care_tasks_assignee_username", "care_tasks", ["assignee_username"], unique=False)
    op.create_index("ix_care_tasks_created_at", "care_tasks", ["created_at"], unique=False)
    op.create_index("ix_care_tasks_updated_at", "care_tasks", ["updated_at"], unique=False)

    op.create_table(
        "handoff_notes",
        sa.Column("note_id", sa.String(length=64), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.organization_id"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.patient_id"), nullable=False),
        sa.Column("author_username", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.String(length=200), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_handoff_notes_organization_id", "handoff_notes", ["organization_id"], unique=False)
    op.create_index("ix_handoff_notes_patient_id", "handoff_notes", ["patient_id"], unique=False)
    op.create_index("ix_handoff_notes_author_username", "handoff_notes", ["author_username"], unique=False)
    op.create_index("ix_handoff_notes_created_at", "handoff_notes", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_handoff_notes_created_at", table_name="handoff_notes")
    op.drop_index("ix_handoff_notes_author_username", table_name="handoff_notes")
    op.drop_index("ix_handoff_notes_patient_id", table_name="handoff_notes")
    op.drop_index("ix_handoff_notes_organization_id", table_name="handoff_notes")
    op.drop_table("handoff_notes")

    op.drop_index("ix_care_tasks_updated_at", table_name="care_tasks")
    op.drop_index("ix_care_tasks_created_at", table_name="care_tasks")
    op.drop_index("ix_care_tasks_assignee_username", table_name="care_tasks")
    op.drop_index("ix_care_tasks_priority", table_name="care_tasks")
    op.drop_index("ix_care_tasks_status", table_name="care_tasks")
    op.drop_index("ix_care_tasks_patient_id", table_name="care_tasks")
    op.drop_index("ix_care_tasks_organization_id", table_name="care_tasks")
    op.drop_table("care_tasks")

    op.drop_index("ix_invite_codes_expires_at", table_name="invite_codes")
    op.drop_index("ix_invite_codes_created_at", table_name="invite_codes")
    op.drop_index("ix_invite_codes_status", table_name="invite_codes")
    op.drop_index("ix_invite_codes_code_hash", table_name="invite_codes")
    op.drop_index("ix_invite_codes_email", table_name="invite_codes")
    op.drop_index("ix_invite_codes_role", table_name="invite_codes")
    op.drop_index("ix_invite_codes_organization_id", table_name="invite_codes")
    op.drop_table("invite_codes")

    op.drop_index("ix_user_sessions_revoked_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_last_used_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_created_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_refresh_token_hash", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")

    with op.batch_alter_table("imaging_studies") as batch_op:
        batch_op.drop_constraint("fk_imaging_studies_organization_id", type_="foreignkey")
        batch_op.drop_index("ix_imaging_studies_organization_id")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("notifications") as batch_op:
        batch_op.drop_constraint("fk_notifications_organization_id", type_="foreignkey")
        batch_op.drop_index("ix_notifications_organization_id")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.drop_constraint("fk_audit_logs_organization_id", type_="foreignkey")
        batch_op.drop_index("ix_audit_logs_organization_id")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("report_jobs") as batch_op:
        batch_op.drop_constraint("fk_report_jobs_organization_id", type_="foreignkey")
        batch_op.drop_index("ix_report_jobs_idempotency_key")
        batch_op.drop_index("ix_report_jobs_organization_id")
        batch_op.drop_column("idempotency_key")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("alerts") as batch_op:
        batch_op.drop_constraint("fk_alerts_organization_id", type_="foreignkey")
        batch_op.drop_index("ix_alerts_organization_id")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("patients") as batch_op:
        batch_op.drop_constraint("fk_patients_organization_id", type_="foreignkey")
        batch_op.drop_index("ix_patients_organization_id")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_organization_id", type_="foreignkey")
        batch_op.drop_index("ix_users_organization_id")
        batch_op.drop_column("organization_id")

    op.drop_index("ix_organizations_status", table_name="organizations")
    op.drop_index("ix_organizations_name", table_name="organizations")
    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_table("organizations")
