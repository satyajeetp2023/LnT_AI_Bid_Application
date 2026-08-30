"""Add ownership to drawing BOQ findings.

Revision ID: 0015
Revises: 0014
"""
from alembic import op
import sqlalchemy as sa

revision="0015"
down_revision="0014"
branch_labels=None
depends_on=None

def upgrade():
 op.add_column("drawing_boq_findings",sa.Column("responsible_function",sa.String(100),nullable=False,server_default="Engineering"))
 op.add_column("drawing_boq_findings",sa.Column("responsible_person",sa.String(200)))
 op.create_index("ix_drawing_boq_responsible_function","drawing_boq_findings",["responsible_function"])

def downgrade():
 op.drop_index("ix_drawing_boq_responsible_function",table_name="drawing_boq_findings")
 op.drop_column("drawing_boq_findings","responsible_person")
 op.drop_column("drawing_boq_findings","responsible_function")
