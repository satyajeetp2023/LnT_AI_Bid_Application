"""add immutable bid decision snapshots

Revision ID: 0023
Revises: 0022
"""
from alembic import op
import sqlalchemy as sa

revision="0023"
down_revision="0022"
branch_labels=None
depends_on=None


def upgrade():
 op.create_table(
  "bid_decision_snapshots",
  sa.Column("id",sa.Integer(),primary_key=True),
  sa.Column("bid_project_id",sa.Integer(),sa.ForeignKey("bid_projects.id",ondelete="CASCADE"),nullable=False),
  sa.Column("snapshot_version",sa.String(80),nullable=False),
  sa.Column("decision_posture",sa.String(60),nullable=False),
  sa.Column("readiness_score",sa.Numeric(6,2),nullable=False),
  sa.Column("confidence_level",sa.String(30),nullable=False),
  sa.Column("payload",sa.JSON(),nullable=False),
  sa.Column("checksum",sa.String(64),nullable=False),
  sa.Column("created_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
  sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
 )
 op.create_index("ix_bid_decision_snapshots_bid_project_id","bid_decision_snapshots",["bid_project_id"])
 op.create_index("ix_bid_decision_snapshots_decision_posture","bid_decision_snapshots",["decision_posture"])
 op.create_index("ix_bid_decision_snapshots_checksum","bid_decision_snapshots",["checksum"])
 op.create_index("ix_bid_decision_snapshots_created_at","bid_decision_snapshots",["created_at"])


def downgrade():
 op.drop_index("ix_bid_decision_snapshots_created_at",table_name="bid_decision_snapshots")
 op.drop_index("ix_bid_decision_snapshots_checksum",table_name="bid_decision_snapshots")
 op.drop_index("ix_bid_decision_snapshots_decision_posture",table_name="bid_decision_snapshots")
 op.drop_index("ix_bid_decision_snapshots_bid_project_id",table_name="bid_decision_snapshots")
 op.drop_table("bid_decision_snapshots")
