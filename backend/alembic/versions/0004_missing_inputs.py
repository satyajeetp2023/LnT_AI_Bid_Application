"""Create missing inputs register.

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision="0004";down_revision="0003";branch_labels=None;depends_on=None

def upgrade():
 op.create_table("bid_missing_inputs",
  sa.Column("id",sa.Integer(),primary_key=True),
  sa.Column("bid_project_id",sa.Integer(),sa.ForeignKey("bid_projects.id",ondelete="CASCADE"),nullable=False),
  sa.Column("requirement_id",sa.Integer(),sa.ForeignKey("bid_requirements.id",ondelete="SET NULL")),
  sa.Column("source_document_id",sa.Integer(),sa.ForeignKey("bid_documents.id",ondelete="SET NULL")),
  sa.Column("missing_input_title",sa.String(300),nullable=False),
  sa.Column("missing_input_description",sa.Text(),nullable=False),
  sa.Column("input_category",sa.String(100),nullable=False),
  sa.Column("input_type",sa.String(100),nullable=False),
  sa.Column("responsible_function",sa.String(100)),
  sa.Column("responsible_person",sa.String(200)),
  sa.Column("requested_from",sa.String(200)),
  sa.Column("required_by_date",sa.Date()),
  sa.Column("priority",sa.String(20),nullable=False),
  sa.Column("status",sa.String(40),nullable=False),
  sa.Column("impact_if_missing",sa.Text()),
  sa.Column("resolution_notes",sa.Text()),
  sa.Column("source_page",sa.String(50)),
  sa.Column("source_clause",sa.String(100)),
  sa.Column("source_section",sa.String(200)),
  sa.Column("source_excerpt",sa.Text()),
  sa.Column("created_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
  sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
  sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
  sa.Column("resolved_by",sa.Integer(),sa.ForeignKey("users.id")),
  sa.Column("resolved_at",sa.DateTime(timezone=True)))
 for name in ["bid_project_id","requirement_id","source_document_id","status","priority","required_by_date","responsible_function"]:
  op.create_index(f"ix_bid_missing_inputs_{name}","bid_missing_inputs",[name])

def downgrade():
 op.drop_table("bid_missing_inputs")
