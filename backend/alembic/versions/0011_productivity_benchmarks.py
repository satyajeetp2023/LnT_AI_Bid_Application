"""Add productivity benchmark learning table.

Revision ID: 0011
Revises: 0010
"""
from alembic import op
import sqlalchemy as sa

revision="0011"
down_revision="0010"
branch_labels=None
depends_on=None

def upgrade():
 op.create_table(
  "productivity_benchmarks",
  sa.Column("id",sa.Integer(),primary_key=True),
  sa.Column("activity_name",sa.String(300),nullable=False),
  sa.Column("activity_key",sa.String(300),nullable=False),
  sa.Column("project_type",sa.String(200)),
  sa.Column("discipline",sa.String(100)),
  sa.Column("unit",sa.String(50),nullable=False),
  sa.Column("rate_per_working_day",sa.Numeric(18,6),nullable=False),
  sa.Column("resource_context",sa.Text()),
  sa.Column("source_type",sa.String(50),nullable=False,server_default="User Confirmed"),
  sa.Column("source_reference",sa.String(300)),
  sa.Column("bid_project_id",sa.Integer(),sa.ForeignKey("bid_projects.id",ondelete="SET NULL")),
  sa.Column("confidence",sa.Numeric(5,4),nullable=False,server_default="0.6000"),
  sa.Column("is_active",sa.Boolean(),nullable=False,server_default=sa.true()),
  sa.Column("notes",sa.Text()),
  sa.Column("created_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
  sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
  sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
 )
 for name,column in (
  ("ix_productivity_benchmarks_activity_name","activity_name"),
  ("ix_productivity_benchmarks_activity_key","activity_key"),
  ("ix_productivity_benchmarks_project_type","project_type"),
  ("ix_productivity_benchmarks_discipline","discipline"),
  ("ix_productivity_benchmarks_unit","unit"),
  ("ix_productivity_benchmarks_source_type","source_type"),
  ("ix_productivity_benchmarks_bid_project_id","bid_project_id"),
  ("ix_productivity_benchmarks_is_active","is_active"),
 ):
  op.create_index(name,"productivity_benchmarks",[column])

def downgrade():
 op.drop_table("productivity_benchmarks")
