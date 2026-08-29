"""Add pre-bid query approval metadata.

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa

revision="0007"
down_revision="0006"
branch_labels=None
depends_on=None

def upgrade():
 op.add_column("bid_pre_bid_queries",sa.Column("approved_by",sa.Integer(),sa.ForeignKey("users.id")))
 op.add_column("bid_pre_bid_queries",sa.Column("approved_at",sa.DateTime(timezone=True)))

def downgrade():
 op.drop_column("bid_pre_bid_queries","approved_at")
 op.drop_column("bid_pre_bid_queries","approved_by")
