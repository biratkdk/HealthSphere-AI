"""imaging review workflow state"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0003_imaging_review_workflow"
down_revision = "0002_enterprise_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("imaging_studies")}
    existing_indexes = {index["name"] for index in inspector.get_indexes("imaging_studies")}

    with op.batch_alter_table("imaging_studies") as batch_op:
        if "priority" not in existing_columns:
            batch_op.add_column(sa.Column("priority", sa.String(length=32), nullable=False, server_default="routine"))
        if "review_status" not in existing_columns:
            batch_op.add_column(sa.Column("review_status", sa.String(length=32), nullable=False, server_default="pending_review"))
        if "review_due_at" not in existing_columns:
            batch_op.add_column(sa.Column("review_due_at", sa.DateTime(timezone=True), nullable=True))
        if "review_notes" not in existing_columns:
            batch_op.add_column(sa.Column("review_notes", sa.Text(), nullable=True))
        if "escalation_reason" not in existing_columns:
            batch_op.add_column(sa.Column("escalation_reason", sa.Text(), nullable=True))
        if "reviewed_by" not in existing_columns:
            batch_op.add_column(sa.Column("reviewed_by", sa.String(length=64), nullable=True))
        if "reviewed_at" not in existing_columns:
            batch_op.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
        if "signed_off_by" not in existing_columns:
            batch_op.add_column(sa.Column("signed_off_by", sa.String(length=64), nullable=True))
        if "signed_off_at" not in existing_columns:
            batch_op.add_column(sa.Column("signed_off_at", sa.DateTime(timezone=True), nullable=True))

    if "ix_imaging_studies_priority" not in existing_indexes:
        op.create_index("ix_imaging_studies_priority", "imaging_studies", ["priority"], unique=False)
    if "ix_imaging_studies_review_status" not in existing_indexes:
        op.create_index("ix_imaging_studies_review_status", "imaging_studies", ["review_status"], unique=False)
    if "ix_imaging_studies_review_due_at" not in existing_indexes:
        op.create_index("ix_imaging_studies_review_due_at", "imaging_studies", ["review_due_at"], unique=False)
    if "ix_imaging_studies_reviewed_by" not in existing_indexes:
        op.create_index("ix_imaging_studies_reviewed_by", "imaging_studies", ["reviewed_by"], unique=False)
    if "ix_imaging_studies_reviewed_at" not in existing_indexes:
        op.create_index("ix_imaging_studies_reviewed_at", "imaging_studies", ["reviewed_at"], unique=False)
    if "ix_imaging_studies_signed_off_by" not in existing_indexes:
        op.create_index("ix_imaging_studies_signed_off_by", "imaging_studies", ["signed_off_by"], unique=False)
    if "ix_imaging_studies_signed_off_at" not in existing_indexes:
        op.create_index("ix_imaging_studies_signed_off_at", "imaging_studies", ["signed_off_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_imaging_studies_signed_off_at", table_name="imaging_studies")
    op.drop_index("ix_imaging_studies_signed_off_by", table_name="imaging_studies")
    op.drop_index("ix_imaging_studies_reviewed_at", table_name="imaging_studies")
    op.drop_index("ix_imaging_studies_reviewed_by", table_name="imaging_studies")
    op.drop_index("ix_imaging_studies_review_due_at", table_name="imaging_studies")
    op.drop_index("ix_imaging_studies_review_status", table_name="imaging_studies")
    op.drop_index("ix_imaging_studies_priority", table_name="imaging_studies")

    with op.batch_alter_table("imaging_studies") as batch_op:
        batch_op.drop_column("signed_off_at")
        batch_op.drop_column("signed_off_by")
        batch_op.drop_column("reviewed_at")
        batch_op.drop_column("reviewed_by")
        batch_op.drop_column("escalation_reason")
        batch_op.drop_column("review_notes")
        batch_op.drop_column("review_due_at")
        batch_op.drop_column("review_status")
        batch_op.drop_column("priority")
