"""Create pre-bid query suggestion decisions.

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa

revision="0006"
down_revision="0005"
branch_labels=None
depends_on=None

def upgrade():
 op.create_table(
  "bid_pre_bid_query_decisions",
  sa.Column("id",sa.Integer(),primary_key=True),
  sa.Column("bid_project_id",sa.Integer(),sa.ForeignKey("bid_projects.id",ondelete="CASCADE"),nullable=False),
  sa.Column("source_kind",sa.String(80),nullable=False),
  sa.Column("source_id",sa.Integer(),nullable=False),
  sa.Column("decision",sa.String(40),nullable=False),
  sa.Column("reason",sa.Text()),
  sa.Column("decided_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
  sa.Column("decided_at",sa.DateTime(timezone=True),nullable=False),
  sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
  sa.UniqueConstraint("bid_project_id","source_kind","source_id",name="uq_pre_bid_query_decision_source"),
 )
 for name in ["bid_project_id","source_kind","source_id","decision"]:
  op.create_index(f"ix_bid_pre_bid_query_decisions_{name}","bid_pre_bid_query_decisions",[name])

def downgrade():
 op.drop_table("bid_pre_bid_query_decisions")
