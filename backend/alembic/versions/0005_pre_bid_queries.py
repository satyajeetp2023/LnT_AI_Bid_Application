"""Create pre-bid query register.

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa
revision="0005";down_revision="0004";branch_labels=None;depends_on=None

def upgrade():
 op.create_table("bid_pre_bid_queries",
  sa.Column("id",sa.Integer(),primary_key=True),
  sa.Column("bid_project_id",sa.Integer(),sa.ForeignKey("bid_projects.id",ondelete="CASCADE"),nullable=False),
  sa.Column("requirement_id",sa.Integer(),sa.ForeignKey("bid_requirements.id",ondelete="SET NULL")),
  sa.Column("missing_input_id",sa.Integer(),sa.ForeignKey("bid_missing_inputs.id",ondelete="SET NULL")),
  sa.Column("source_document_id",sa.Integer(),sa.ForeignKey("bid_documents.id",ondelete="SET NULL")),
  sa.Column("query_number",sa.String(100)),
  sa.Column("query_title",sa.String(300),nullable=False),
  sa.Column("query_text",sa.Text(),nullable=False),
  sa.Column("query_category",sa.String(100),nullable=False),
  sa.Column("responsible_function",sa.String(100)),
  sa.Column("responsible_person",sa.String(200)),
  sa.Column("priority",sa.String(20),nullable=False),
  sa.Column("status",sa.String(40),nullable=False),
  sa.Column("target_response_date",sa.Date()),
  sa.Column("submitted_date",sa.Date()),
  sa.Column("employer_response",sa.Text()),
  sa.Column("response_date",sa.Date()),
  sa.Column("response_reference",sa.String(200)),
  sa.Column("impact_if_unresolved",sa.Text()),
  sa.Column("source_page",sa.String(50)),
  sa.Column("source_clause",sa.String(100)),
  sa.Column("source_section",sa.String(200)),
  sa.Column("source_excerpt",sa.Text()),
  sa.Column("created_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
  sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
  sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
  sa.Column("closed_by",sa.Integer(),sa.ForeignKey("users.id")),
  sa.Column("closed_at",sa.DateTime(timezone=True)))
 for name in ["bid_project_id","requirement_id","missing_input_id","source_document_id","status","priority","target_response_date","responsible_function"]:op.create_index(f"ix_bid_pre_bid_queries_{name}","bid_pre_bid_queries",[name])

def downgrade():op.drop_table("bid_pre_bid_queries")
