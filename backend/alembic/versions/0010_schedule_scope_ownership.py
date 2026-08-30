"""Add ownership to schedule scope items.

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa

revision="0010"
down_revision="0009"
branch_labels=None
depends_on=None

def upgrade():
 op.add_column("schedule_scope_items",sa.Column("responsible_function",sa.String(100),nullable=False,server_default="Planning"))
 op.add_column("schedule_scope_items",sa.Column("responsible_person",sa.String(200)))
 op.create_index("ix_schedule_scope_responsible_function","schedule_scope_items",["responsible_function"])

def downgrade():
 op.drop_index("ix_schedule_scope_responsible_function",table_name="schedule_scope_items")
 op.drop_column("schedule_scope_items","responsible_person")
 op.drop_column("schedule_scope_items","responsible_function")
