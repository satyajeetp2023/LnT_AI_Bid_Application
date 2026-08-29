"""Add schedule scope coverage register.

Revision ID: 0009
Revises: 0008
"""
from alembic import op
import sqlalchemy as sa

revision="0009"
down_revision="0008"
branch_labels=None
depends_on=None

def upgrade():
 op.create_table(
  "schedule_scope_items",
  sa.Column("id",sa.Integer(),primary_key=True),
  sa.Column("bid_project_id",sa.Integer(),sa.ForeignKey("bid_projects.id",ondelete="CASCADE"),nullable=False),
  sa.Column("parent_id",sa.Integer(),sa.ForeignKey("schedule_scope_items.id",ondelete="CASCADE")),
  sa.Column("source_requirement_id",sa.Integer(),sa.ForeignKey("bid_requirements.id",ondelete="SET NULL")),
  sa.Column("source_document_id",sa.Integer(),sa.ForeignKey("bid_documents.id",ondelete="SET NULL")),
  sa.Column("activity_name",sa.String(300),nullable=False),
  sa.Column("activity_level",sa.String(40),nullable=False,server_default="Activity"),
  sa.Column("source_type",sa.String(60),nullable=False),
  sa.Column("source_reference",sa.String(200)),
  sa.Column("source_excerpt",sa.Text()),
  sa.Column("mandatory",sa.Boolean(),nullable=False,server_default=sa.text("true")),
  sa.Column("match_keywords",sa.JSON(),nullable=False,server_default=sa.text("'[]'")),
  sa.Column("coverage_status",sa.String(40),nullable=False,server_default="Not Checked"),
  sa.Column("matched_task_code",sa.String(100)),
  sa.Column("matched_task_name",sa.String(500)),
  sa.Column("match_confidence",sa.Numeric(5,4)),
  sa.Column("disposition_status",sa.String(40),nullable=False,server_default="Unexplained"),
  sa.Column("disposition_reason",sa.Text()),
  sa.Column("disposition_by",sa.Integer(),sa.ForeignKey("users.id")),
  sa.Column("disposition_at",sa.DateTime(timezone=True)),
  sa.Column("created_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
  sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
  sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
 )
 op.create_index("ix_schedule_scope_bid","schedule_scope_items",["bid_project_id"])
 op.create_index("ix_schedule_scope_parent","schedule_scope_items",["parent_id"])
 op.create_index("ix_schedule_scope_requirement","schedule_scope_items",["source_requirement_id"])
 op.create_index("ix_schedule_scope_document","schedule_scope_items",["source_document_id"])
 op.create_index("ix_schedule_scope_source_type","schedule_scope_items",["source_type"])
 op.create_index("ix_schedule_scope_coverage","schedule_scope_items",["coverage_status"])
 op.create_index("ix_schedule_scope_disposition","schedule_scope_items",["disposition_status"])

def downgrade():
 op.drop_table("schedule_scope_items")
