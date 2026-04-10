"""report job workflow state"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0002_report_job_workflow_state"
down_revision = "0001_initial_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("report_jobs")}
    existing_indexes = {index["name"] for index in inspector.get_indexes("report_jobs")}

    if "workflow_stage" not in existing_columns:
        op.add_column("report_jobs", sa.Column("workflow_stage", sa.String(length=64), nullable=False, server_default="queued"))
    if "progress_percent" not in existing_columns:
        op.add_column("report_jobs", sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"))
    if "attempt_count" not in existing_columns:
        op.add_column("report_jobs", sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"))
    if "max_attempts" not in existing_columns:
        op.add_column("report_jobs", sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"))
    if "next_attempt_at" not in existing_columns:
        op.add_column("report_jobs", sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True))
    if "lease_expires_at" not in existing_columns:
        op.add_column("report_jobs", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
    if "worker_id" not in existing_columns:
        op.add_column("report_jobs", sa.Column("worker_id", sa.String(length=128), nullable=True))

    if "ix_report_jobs_workflow_stage" not in existing_indexes:
        op.create_index("ix_report_jobs_workflow_stage", "report_jobs", ["workflow_stage"], unique=False)
    if "ix_report_jobs_next_attempt_at" not in existing_indexes:
        op.create_index("ix_report_jobs_next_attempt_at", "report_jobs", ["next_attempt_at"], unique=False)
    if "ix_report_jobs_lease_expires_at" not in existing_indexes:
        op.create_index("ix_report_jobs_lease_expires_at", "report_jobs", ["lease_expires_at"], unique=False)
    if "ix_report_jobs_worker_id" not in existing_indexes:
        op.create_index("ix_report_jobs_worker_id", "report_jobs", ["worker_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_report_jobs_worker_id", table_name="report_jobs")
    op.drop_index("ix_report_jobs_lease_expires_at", table_name="report_jobs")
    op.drop_index("ix_report_jobs_next_attempt_at", table_name="report_jobs")
    op.drop_index("ix_report_jobs_workflow_stage", table_name="report_jobs")
    op.drop_column("report_jobs", "worker_id")
    op.drop_column("report_jobs", "lease_expires_at")
    op.drop_column("report_jobs", "next_attempt_at")
    op.drop_column("report_jobs", "max_attempts")
    op.drop_column("report_jobs", "attempt_count")
    op.drop_column("report_jobs", "progress_percent")
    op.drop_column("report_jobs", "workflow_stage")
