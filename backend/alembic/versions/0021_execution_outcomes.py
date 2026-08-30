"""add reviewed execution outcomes for Phase 8

Revision ID: 0021
Revises: 0020
"""
from alembic import op
import sqlalchemy as sa

revision="0021"
down_revision="0020"
branch_labels=None
depends_on=None


def upgrade():
 op.create_table(
  "execution_outcomes",
  sa.Column("id",sa.Integer(),primary_key=True),
  sa.Column("bid_project_id",sa.Integer(),sa.ForeignKey("bid_projects.id",ondelete="CASCADE"),nullable=False),
  sa.Column("execution_status",sa.String(30),nullable=False,server_default="Not Started"),
  sa.Column("data_date",sa.Date()),
  sa.Column("actual_start_date",sa.Date()),
  sa.Column("actual_completion_date",sa.Date()),
  sa.Column("final_contract_value",sa.Numeric(18,2)),
  sa.Column("actual_cost",sa.Numeric(18,2)),
  sa.Column("final_margin_percent",sa.Numeric(7,3)),
  sa.Column("approved_variations",sa.Numeric(18,2)),
  sa.Column("claims_recovered",sa.Numeric(18,2)),
  sa.Column("eot_days",sa.Integer()),
  sa.Column("source_reference",sa.String(500)),
  sa.Column("notes",sa.Text()),
  sa.Column("review_status",sa.String(20),nullable=False,server_default="Draft"),
  sa.Column("reviewed_by",sa.Integer(),sa.ForeignKey("users.id")),
  sa.Column("reviewed_at",sa.DateTime(timezone=True)),
  sa.Column("created_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
  sa.Column("updated_by",sa.Integer(),sa.ForeignKey("users.id")),
  sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
  sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
  sa.CheckConstraint("execution_status IN ('Not Started','In Progress','Completed','Closed')",name="ck_execution_status"),
  sa.CheckConstraint("review_status IN ('Draft','Reviewed')",name="ck_execution_review_status"),
  sa.CheckConstraint("final_contract_value IS NULL OR final_contract_value >= 0",name="ck_execution_final_value"),
  sa.CheckConstraint("actual_cost IS NULL OR actual_cost >= 0",name="ck_execution_actual_cost"),
  sa.CheckConstraint("final_margin_percent IS NULL OR (final_margin_percent >= -100 AND final_margin_percent <= 100)",name="ck_execution_margin"),
  sa.CheckConstraint("approved_variations IS NULL OR approved_variations >= 0",name="ck_execution_variations"),
  sa.CheckConstraint("claims_recovered IS NULL OR claims_recovered >= 0",name="ck_execution_claims"),
  sa.CheckConstraint("eot_days IS NULL OR eot_days >= 0",name="ck_execution_eot"),
  sa.CheckConstraint("actual_completion_date IS NULL OR actual_start_date IS NULL OR actual_completion_date >= actual_start_date",name="ck_execution_dates"),
  sa.UniqueConstraint("bid_project_id",name="uq_execution_outcome_bid"),
 )
 op.create_index("ix_execution_outcomes_bid_project_id","execution_outcomes",["bid_project_id"],unique=True)
 op.create_index("ix_execution_outcomes_execution_status","execution_outcomes",["execution_status"])
 op.create_index("ix_execution_outcomes_review_status","execution_outcomes",["review_status"])
 op.create_index("ix_execution_outcomes_data_date","execution_outcomes",["data_date"])


def downgrade():
 op.drop_index("ix_execution_outcomes_data_date",table_name="execution_outcomes")
 op.drop_index("ix_execution_outcomes_review_status",table_name="execution_outcomes")
 op.drop_index("ix_execution_outcomes_execution_status",table_name="execution_outcomes")
 op.drop_index("ix_execution_outcomes_bid_project_id",table_name="execution_outcomes")
 op.drop_table("execution_outcomes")
