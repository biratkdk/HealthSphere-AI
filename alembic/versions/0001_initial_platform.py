"""initial platform schema"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_platform"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("auth_provider", sa.String(length=32), nullable=False, server_default="local"),
        sa.Column("external_subject", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("preferences", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("external_subject"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"], unique=False)
    op.create_index("ix_users_auth_provider", "users", ["auth_provider"], unique=False)
    op.create_index("ix_users_external_subject", "users", ["external_subject"], unique=True)

    op.create_table(
        "patients",
        sa.Column("patient_id", sa.Integer(), primary_key=True),
        sa.Column("mrn", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("sex", sa.String(length=16), nullable=False),
        sa.Column("care_unit", sa.String(length=64), nullable=False),
        sa.Column("diagnosis", sa.String(length=256), nullable=False),
        sa.Column("heart_rate", sa.Integer(), nullable=False),
        sa.Column("respiratory_rate", sa.Integer(), nullable=False),
        sa.Column("systolic_bp", sa.Integer(), nullable=False),
        sa.Column("temperature_c", sa.Float(), nullable=False),
        sa.Column("oxygen_saturation", sa.Integer(), nullable=False),
        sa.Column("pain_score", sa.Integer(), nullable=False),
        sa.Column("medications", sa.JSON(), nullable=False),
        sa.Column("risk_flags", sa.JSON(), nullable=False),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("mrn"),
    )
    op.create_index("ix_patients_mrn", "patients", ["mrn"], unique=True)
    op.create_index("ix_patients_name", "patients", ["name"], unique=False)
    op.create_index("ix_patients_care_unit", "patients", ["care_unit"], unique=False)

    op.create_table(
        "lab_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.patient_id"), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_lab_results_patient_id", "lab_results", ["patient_id"], unique=False)
    op.create_index("ix_lab_results_name", "lab_results", ["name"], unique=False)

    op.create_table(
        "imaging_findings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.patient_id"), nullable=False),
        sa.Column("modality", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_imaging_findings_patient_id", "imaging_findings", ["patient_id"], unique=False)

    op.create_table(
        "alerts",
        sa.Column("alert_id", sa.String(length=64), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.patient_id"), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_alerts_patient_id", "alerts", ["patient_id"], unique=False)
    op.create_index("ix_alerts_severity", "alerts", ["severity"], unique=False)
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"], unique=False)

    op.create_table(
        "report_jobs",
        sa.Column("job_id", sa.String(length=64), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.patient_id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("artifact_payload", sa.JSON(), nullable=True),
        sa.Column("artifact_uri", sa.String(length=512), nullable=True),
        sa.Column("task_id", sa.String(length=128), nullable=True),
        sa.Column("requested_by", sa.String(length=64), nullable=True),
        sa.Column("delivery_status", sa.String(length=32), nullable=False, server_default="pending"),
    )
    op.create_index("ix_report_jobs_patient_id", "report_jobs", ["patient_id"], unique=False)
    op.create_index("ix_report_jobs_status", "report_jobs", ["status"], unique=False)
    op.create_index("ix_report_jobs_created_at", "report_jobs", ["created_at"], unique=False)
    op.create_index("ix_report_jobs_task_id", "report_jobs", ["task_id"], unique=False)
    op.create_index("ix_report_jobs_requested_by", "report_jobs", ["requested_by"], unique=False)
    op.create_index("ix_report_jobs_delivery_status", "report_jobs", ["delivery_status"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("audit_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("actor_username", sa.String(length=64), nullable=False),
        sa.Column("actor_role", sa.String(length=32), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("path", sa.String(length=256), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"], unique=False)
    op.create_index("ix_audit_logs_actor_username", "audit_logs", ["actor_username"], unique=False)
    op.create_index("ix_audit_logs_actor_role", "audit_logs", ["actor_role"], unique=False)
    op.create_index("ix_audit_logs_path", "audit_logs", ["path"], unique=False)
    op.create_index("ix_audit_logs_status_code", "audit_logs", ["status_code"], unique=False)
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("notification_id", sa.String(length=64), primary_key=True),
        sa.Column("recipient_username", sa.String(length=64), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.patient_id"), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_notifications_recipient_username", "notifications", ["recipient_username"], unique=False)
    op.create_index("ix_notifications_patient_id", "notifications", ["patient_id"], unique=False)
    op.create_index("ix_notifications_severity", "notifications", ["severity"], unique=False)
    op.create_index("ix_notifications_category", "notifications", ["category"], unique=False)
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"], unique=False)
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"], unique=False)

    op.create_table(
        "imaging_studies",
        sa.Column("study_id", sa.String(length=64), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.patient_id"), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("storage_uri", sa.String(length=512), nullable=False),
        sa.Column("uploaded_by", sa.String(length=64), nullable=False),
        sa.Column("analysis_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_imaging_studies_patient_id", "imaging_studies", ["patient_id"], unique=False)
    op.create_index("ix_imaging_studies_uploaded_by", "imaging_studies", ["uploaded_by"], unique=False)
    op.create_index("ix_imaging_studies_created_at", "imaging_studies", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_imaging_studies_created_at", table_name="imaging_studies")
    op.drop_index("ix_imaging_studies_uploaded_by", table_name="imaging_studies")
    op.drop_index("ix_imaging_studies_patient_id", table_name="imaging_studies")
    op.drop_table("imaging_studies")

    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_index("ix_notifications_category", table_name="notifications")
    op.drop_index("ix_notifications_severity", table_name="notifications")
    op.drop_index("ix_notifications_patient_id", table_name="notifications")
    op.drop_index("ix_notifications_recipient_username", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_status_code", table_name="audit_logs")
    op.drop_index("ix_audit_logs_path", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_role", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_username", table_name="audit_logs")
    op.drop_index("ix_audit_logs_request_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_report_jobs_delivery_status", table_name="report_jobs")
    op.drop_index("ix_report_jobs_requested_by", table_name="report_jobs")
    op.drop_index("ix_report_jobs_task_id", table_name="report_jobs")
    op.drop_index("ix_report_jobs_created_at", table_name="report_jobs")
    op.drop_index("ix_report_jobs_status", table_name="report_jobs")
    op.drop_index("ix_report_jobs_patient_id", table_name="report_jobs")
    op.drop_table("report_jobs")

    op.drop_index("ix_alerts_created_at", table_name="alerts")
    op.drop_index("ix_alerts_severity", table_name="alerts")
    op.drop_index("ix_alerts_patient_id", table_name="alerts")
    op.drop_table("alerts")

    op.drop_index("ix_imaging_findings_patient_id", table_name="imaging_findings")
    op.drop_table("imaging_findings")

    op.drop_index("ix_lab_results_name", table_name="lab_results")
    op.drop_index("ix_lab_results_patient_id", table_name="lab_results")
    op.drop_table("lab_results")

    op.drop_index("ix_patients_care_unit", table_name="patients")
    op.drop_index("ix_patients_name", table_name="patients")
    op.drop_index("ix_patients_mrn", table_name="patients")
    op.drop_table("patients")

    op.drop_index("ix_users_external_subject", table_name="users")
    op.drop_index("ix_users_auth_provider", table_name="users")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
