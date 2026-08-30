"""Add bidder planning resource and staff plan entries.

Revision ID: 0017
Revises: 0016
"""
from alembic import op
import sqlalchemy as sa

revision="0017"
down_revision="0016"
branch_labels=None
depends_on=None

def upgrade():
 op.create_table(
  "planning_resource_entries",
  sa.Column("id",sa.Integer(),primary_key=True),
  sa.Column("bid_project_id",sa.Integer(),sa.ForeignKey("bid_projects.id",ondelete="CASCADE"),nullable=False),
  sa.Column("source_document_id",sa.Integer(),sa.ForeignKey("bid_documents.id",ondelete="CASCADE"),nullable=False),
  sa.Column("source_sheet",sa.String(200)),
  sa.Column("source_row",sa.Integer(),nullable=False),
  sa.Column("plan_type",sa.String(40),nullable=False),
  sa.Column("resource_category",sa.String(40),nullable=False),
  sa.Column("resource_name",sa.String(250),nullable=False),
  sa.Column("role_or_trade",sa.String(200)),
  sa.Column("activity_reference",sa.String(300)),
  sa.Column("work_front",sa.String(250)),
  sa.Column("quantity",sa.Numeric(18,4)),
  sa.Column("unit",sa.String(40)),
  sa.Column("start_date",sa.Date()),
  sa.Column("finish_date",sa.Date()),
  sa.Column("shift_hours",sa.Numeric(10,2)),
  sa.Column("productivity_rate",sa.Numeric(18,6)),
  sa.Column("productivity_unit",sa.String(80)),
  sa.Column("notes",sa.Text()),
  sa.Column("extraction_confidence",sa.Numeric(5,4),nullable=False),
  sa.Column("created_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
  sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
  sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
  sa.UniqueConstraint("source_document_id","source_sheet","source_row",name="uq_planning_resource_source_row"),
 )
 for name,column in (
  ("ix_planning_resource_bid","bid_project_id"),
  ("ix_planning_resource_document","source_document_id"),
  ("ix_planning_resource_plan_type","plan_type"),
  ("ix_planning_resource_category","resource_category"),
  ("ix_planning_resource_name","resource_name"),
  ("ix_planning_resource_role","role_or_trade"),
  ("ix_planning_resource_activity","activity_reference"),
  ("ix_planning_resource_work_front","work_front"),
  ("ix_planning_resource_start","start_date"),
  ("ix_planning_resource_finish","finish_date"),
 ):
  op.create_index(name,"planning_resource_entries",[column])

def downgrade():
 op.drop_table("planning_resource_entries")
