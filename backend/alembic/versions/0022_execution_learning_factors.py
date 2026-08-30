"""add reviewed execution learning factors

Revision ID: 0022
Revises: 0021
"""
from alembic import op
import sqlalchemy as sa

revision="0022"
down_revision="0021"
branch_labels=None
depends_on=None


def upgrade():
 op.create_table(
  "execution_learning_factors",
  sa.Column("id",sa.Integer(),primary_key=True),
  sa.Column("bid_project_id",sa.Integer(),sa.ForeignKey("bid_projects.id",ondelete="CASCADE"),nullable=False),
  sa.Column("execution_outcome_id",sa.Integer(),sa.ForeignKey("execution_outcomes.id",ondelete="CASCADE"),nullable=False),
  sa.Column("factor_category",sa.String(80),nullable=False),
  sa.Column("impact_area",sa.String(30),nullable=False),
  sa.Column("direction",sa.String(20),nullable=False),
  sa.Column("title",sa.String(300),nullable=False),
  sa.Column("description",sa.Text(),nullable=False),
  sa.Column("quantified_impact",sa.Numeric(18,3)),
  sa.Column("impact_unit",sa.String(40)),
  sa.Column("source_reference",sa.String(500)),
  sa.Column("source_excerpt",sa.Text()),
  sa.Column("lesson_for_future_bids",sa.Text()),
  sa.Column("review_status",sa.String(20),nullable=False,server_default="Draft"),
  sa.Column("reviewed_by",sa.Integer(),sa.ForeignKey("users.id")),
  sa.Column("reviewed_at",sa.DateTime(timezone=True)),
  sa.Column("created_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
  sa.Column("updated_by",sa.Integer(),sa.ForeignKey("users.id")),
  sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
  sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
  sa.CheckConstraint("impact_area IN ('Cost','Time','Margin','Revenue','Productivity','Scope','Mixed')",name="ck_execution_factor_area"),
  sa.CheckConstraint("direction IN ('Adverse','Favorable','Neutral')",name="ck_execution_factor_direction"),
  sa.CheckConstraint("review_status IN ('Draft','Reviewed')",name="ck_execution_factor_review"),
  sa.CheckConstraint("quantified_impact IS NULL OR quantified_impact >= 0",name="ck_execution_factor_impact"),
 )
 op.create_index("ix_execution_learning_factors_bid_project_id","execution_learning_factors",["bid_project_id"])
 op.create_index("ix_execution_learning_factors_execution_outcome_id","execution_learning_factors",["execution_outcome_id"])
 op.create_index("ix_execution_learning_factors_factor_category","execution_learning_factors",["factor_category"])
 op.create_index("ix_execution_learning_factors_impact_area","execution_learning_factors",["impact_area"])
 op.create_index("ix_execution_learning_factors_direction","execution_learning_factors",["direction"])
 op.create_index("ix_execution_learning_factors_review_status","execution_learning_factors",["review_status"])


def downgrade():
 op.drop_index("ix_execution_learning_factors_review_status",table_name="execution_learning_factors")
 op.drop_index("ix_execution_learning_factors_direction",table_name="execution_learning_factors")
 op.drop_index("ix_execution_learning_factors_impact_area",table_name="execution_learning_factors")
 op.drop_index("ix_execution_learning_factors_factor_category",table_name="execution_learning_factors")
 op.drop_index("ix_execution_learning_factors_execution_outcome_id",table_name="execution_learning_factors")
 op.drop_index("ix_execution_learning_factors_bid_project_id",table_name="execution_learning_factors")
 op.drop_table("execution_learning_factors")
