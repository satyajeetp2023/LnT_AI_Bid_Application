"""Add ownership to clause risk findings.

Revision ID: 0013
Revises: 0012
"""
from alembic import op
import sqlalchemy as sa

revision="0013"
down_revision="0012"
branch_labels=None
depends_on=None

def upgrade():
 op.add_column("bid_clause_risk_findings",sa.Column("responsible_function",sa.String(100),nullable=False,server_default="Contracts"))
 op.add_column("bid_clause_risk_findings",sa.Column("responsible_person",sa.String(200)))
 op.create_index("ix_clause_risk_responsible_function","bid_clause_risk_findings",["responsible_function"])

def downgrade():
 op.drop_index("ix_clause_risk_responsible_function",table_name="bid_clause_risk_findings")
 op.drop_column("bid_clause_risk_findings","responsible_person")
 op.drop_column("bid_clause_risk_findings","responsible_function")
