"""harden historical bid result constraints

Revision ID: 0020
Revises: 0019
"""
from alembic import op

revision="0020"
down_revision="0019"
branch_labels=None
depends_on=None


def upgrade():
 op.create_check_constraint("ck_bid_outcome_status","bid_outcomes","result_status IN ('Pending','Won','Lost','No Bid','Cancelled','Result Awaited')")
 op.create_check_constraint("ck_bid_outcome_rank","bid_outcomes","our_rank IS NULL OR (our_rank >= 1 AND our_rank <= 100)")
 op.create_check_constraint("ck_bid_outcome_value","bid_outcomes","our_bid_value IS NULL OR our_bid_value >= 0")
 op.create_check_constraint("ck_bid_outcome_margin","bid_outcomes","our_margin_percent IS NULL OR (our_margin_percent >= -100 AND our_margin_percent <= 100)")
 op.create_check_constraint("ck_bid_price_rank","bid_price_records","rank >= 1 AND rank <= 100")
 op.create_check_constraint("ck_bid_price_value","bid_price_records","bid_value >= 0")


def downgrade():
 op.drop_constraint("ck_bid_price_value","bid_price_records",type_="check")
 op.drop_constraint("ck_bid_price_rank","bid_price_records",type_="check")
 op.drop_constraint("ck_bid_outcome_margin","bid_outcomes",type_="check")
 op.drop_constraint("ck_bid_outcome_value","bid_outcomes",type_="check")
 op.drop_constraint("ck_bid_outcome_rank","bid_outcomes",type_="check")
 op.drop_constraint("ck_bid_outcome_status","bid_outcomes",type_="check")
