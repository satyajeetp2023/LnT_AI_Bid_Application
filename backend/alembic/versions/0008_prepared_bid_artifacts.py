"""Add prepared bid artifacts.

Revision ID: 0008
Revises: 0007
"""
from alembic import op
import sqlalchemy as sa

revision="0008"
down_revision="0007"
branch_labels=None
depends_on=None

def upgrade():
 op.create_table(
  "bid_prepared_artifacts",
  sa.Column("id",sa.Integer(),primary_key=True),
  sa.Column("bid_project_id",sa.Integer(),sa.ForeignKey("bid_projects.id",ondelete="CASCADE"),nullable=False),
  sa.Column("template_document_id",sa.Integer(),sa.ForeignKey("bid_documents.id",ondelete="CASCADE"),nullable=False),
  sa.Column("artifact_name",sa.String(300),nullable=False),
  sa.Column("artifact_type",sa.String(100),nullable=False,server_default="Employer Template"),
  sa.Column("file_extension",sa.String(12),nullable=False,server_default="xlsx"),
  sa.Column("storage_path",sa.String(500),nullable=False),
  sa.Column("checksum",sa.String(64),nullable=False),
  sa.Column("file_size",sa.Integer(),nullable=False),
  sa.Column("version_no",sa.Integer(),nullable=False,server_default="1"),
  sa.Column("status",sa.String(40),nullable=False,server_default="Draft"),
  sa.Column("generation_summary",sa.JSON(),nullable=False,server_default=sa.text("'{}'")),
  sa.Column("notes",sa.Text()),
  sa.Column("created_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
  sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
  sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
  sa.Column("ready_for_review_by",sa.Integer(),sa.ForeignKey("users.id")),
  sa.Column("ready_for_review_at",sa.DateTime(timezone=True)),
  sa.Column("approved_by",sa.Integer(),sa.ForeignKey("users.id")),
  sa.Column("approved_at",sa.DateTime(timezone=True)),
 )
 op.create_index("ix_prepared_artifact_bid","bid_prepared_artifacts",["bid_project_id"])
 op.create_index("ix_prepared_artifact_template","bid_prepared_artifacts",["template_document_id"])
 op.create_index("ix_prepared_artifact_status","bid_prepared_artifacts",["status"])
 op.create_index("ix_prepared_artifact_checksum","bid_prepared_artifacts",["checksum"])

def downgrade():
 op.drop_table("bid_prepared_artifacts")
