"""Add historical bid outcome and ranked price records.

Revision ID: 0019
Revises: 0018
"""
from alembic import op
import sqlalchemy as sa

revision="0019"
down_revision="0018"
branch_labels=None
depends_on=None


def upgrade():
 op.create_table(
  "bid_outcomes",
  sa.Column("id",sa.Integer(),primary_key=True),
  sa.Column("bid_project_id",sa.Integer(),sa.ForeignKey("bid_projects.id",ondelete="CASCADE"),nullable=False),
  sa.Column("result_status",sa.String(40),nullable=False,server_default="Pending"),
  sa.Column("result_date",sa.Date()),
  sa.Column("our_rank",sa.Integer()),
  sa.Column("our_bid_value",sa.Numeric(18,2)),
  sa.Column("our_margin_percent",sa.Numeric(7,3)),
  sa.Column("awarded_bidder",sa.String(200)),
  sa.Column("win_reason",sa.Text()),
  sa.Column("loss_reason",sa.Text()),
  sa.Column("source_reference",sa.String(500)),
  sa.Column("notes",sa.Text()),
  sa.Column("created_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
  sa.Column("updated_by",sa.Integer(),sa.ForeignKey("users.id")),
  sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
  sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
  sa.UniqueConstraint("bid_project_id",name="uq_bid_outcome_project"),
 )
 op.create_index("ix_bid_outcome_project","bid_outcomes",["bid_project_id"])
 op.create_index("ix_bid_outcome_status","bid_outcomes",["result_status"])
 op.create_table(
  "bid_price_records",
  sa.Column("id",sa.Integer(),primary_key=True),
  sa.Column("bid_project_id",sa.Integer(),sa.ForeignKey("bid_projects.id",ondelete="CASCADE"),nullable=False),
  sa.Column("bidder_name",sa.String(200),nullable=False),
  sa.Column("rank",sa.Integer(),nullable=False),
  sa.Column("bid_value",sa.Numeric(18,2),nullable=False),
  sa.Column("currency",sa.String(3),nullable=False,server_default="INR"),
  sa.Column("is_ours",sa.Boolean(),nullable=False,server_default=sa.false()),
  sa.Column("source_reference",sa.String(500)),
  sa.Column("created_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
  sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
  sa.UniqueConstraint("bid_project_id","rank",name="uq_bid_price_rank"),
  sa.UniqueConstraint("bid_project_id","bidder_name",name="uq_bid_price_bidder"),
 )
 for name,column in (
  ("ix_bid_price_project","bid_project_id"),
  ("ix_bid_price_bidder","bidder_name"),
  ("ix_bid_price_rank","rank"),
  ("ix_bid_price_ours","is_ours"),
 ):
  op.create_index(name,"bid_price_records",[column])


def downgrade():
 op.drop_table("bid_price_records")
 op.drop_table("bid_outcomes")
