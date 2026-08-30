"""Add integrated planning package findings.

Revision ID: 0018
Revises: 0017
"""
from alembic import op
import sqlalchemy as sa

revision="0018"
down_revision="0017"
branch_labels=None
depends_on=None

def upgrade():
 op.create_table(
  "planning_package_findings",
  sa.Column("id",sa.Integer(),primary_key=True),
  sa.Column("bid_project_id",sa.Integer(),sa.ForeignKey("bid_projects.id",ondelete="CASCADE"),nullable=False),
  sa.Column("schedule_document_id",sa.Integer(),sa.ForeignKey("bid_documents.id",ondelete="SET NULL")),
  sa.Column("finding_key",sa.String(300),nullable=False),
  sa.Column("finding_type",sa.String(80),nullable=False),
  sa.Column("severity",sa.String(20),nullable=False),
  sa.Column("title",sa.String(300),nullable=False),
  sa.Column("description",sa.Text(),nullable=False),
  sa.Column("task_code",sa.String(120)),
  sa.Column("task_name",sa.String(300)),
  sa.Column("source_reference",sa.String(300)),
  sa.Column("responsible_function",sa.String(100),nullable=False,server_default="Planning"),
  sa.Column("responsible_person",sa.String(200)),
  sa.Column("status",sa.String(40),nullable=False,server_default="Open"),
  sa.Column("disposition",sa.String(80)),
  sa.Column("reviewer_comment",sa.Text()),
  sa.Column("reviewed_by",sa.Integer(),sa.ForeignKey("users.id")),
  sa.Column("reviewed_at",sa.DateTime(timezone=True)),
  sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
  sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
  sa.UniqueConstraint("bid_project_id","finding_key",name="uq_planning_package_finding_key"),
 )
 for name,column in (
  ("ix_planning_package_finding_bid","bid_project_id"),
  ("ix_planning_package_finding_schedule","schedule_document_id"),
  ("ix_planning_package_finding_type","finding_type"),
  ("ix_planning_package_finding_severity","severity"),
  ("ix_planning_package_finding_task","task_code"),
  ("ix_planning_package_finding_owner","responsible_function"),
  ("ix_planning_package_finding_status","status"),
 ):
  op.create_index(name,"planning_package_findings",[column])

def downgrade():
 op.drop_table("planning_package_findings")
