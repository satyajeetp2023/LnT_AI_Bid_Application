"""Create manual requirement register.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa
revision="0003";down_revision="0002";branch_labels=None;depends_on=None
def upgrade():
 op.create_table("bid_requirements",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("bid_project_id",sa.Integer(),sa.ForeignKey("bid_projects.id",ondelete="CASCADE"),nullable=False),sa.Column("source_document_id",sa.Integer(),sa.ForeignKey("bid_documents.id",ondelete="SET NULL")),sa.Column("requirement_category",sa.String(100),nullable=False),sa.Column("requirement_type",sa.String(100)),sa.Column("requirement_title",sa.String(300),nullable=False),sa.Column("requirement_text",sa.Text(),nullable=False),sa.Column("source_page",sa.String(50)),sa.Column("source_clause",sa.String(100)),sa.Column("source_section",sa.String(200)),sa.Column("source_excerpt",sa.Text()),sa.Column("responsible_function",sa.String(100)),sa.Column("responsible_person",sa.String(200)),sa.Column("due_date",sa.Date()),sa.Column("priority",sa.String(20),nullable=False),sa.Column("requirement_status",sa.String(40),nullable=False),sa.Column("is_mandatory",sa.Boolean(),nullable=False),sa.Column("compliance_status",sa.String(40),nullable=False),sa.Column("review_status",sa.String(40),nullable=False),sa.Column("reviewed_by",sa.Integer(),sa.ForeignKey("users.id")),sa.Column("reviewed_at",sa.DateTime(timezone=True)),sa.Column("extraction_method",sa.String(40),nullable=False),sa.Column("extraction_confidence",sa.Numeric(5,4)),sa.Column("created_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),sa.Column("notes",sa.Text()))
 for name in ["bid_project_id","source_document_id","requirement_category","requirement_status","priority","due_date"]: op.create_index(f"ix_bid_requirements_{name}","bid_requirements",[name])
def downgrade(): op.drop_table("bid_requirements")
