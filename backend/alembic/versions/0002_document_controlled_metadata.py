"""Add controlled Phase 1 document metadata.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision="0002"
down_revision="0001"
branch_labels=None
depends_on=None

def upgrade():
 op.add_column("bid_documents",sa.Column("document_type",sa.String(100),nullable=True))
 op.add_column("bid_documents",sa.Column("document_number",sa.String(100),nullable=True))
 op.add_column("bid_documents",sa.Column("document_title",sa.String(300),nullable=True))
 op.add_column("bid_documents",sa.Column("revision",sa.String(50),nullable=True))
 op.add_column("bid_documents",sa.Column("document_date",sa.Date(),nullable=True))
 op.add_column("bid_documents",sa.Column("classification_status",sa.String(40),nullable=True))
 op.add_column("bid_documents",sa.Column("classification_confidence",sa.Numeric(5,4),nullable=True))
 op.add_column("bid_documents",sa.Column("is_latest_version",sa.Boolean(),nullable=True))
 op.add_column("bid_documents",sa.Column("remarks",sa.Text(),nullable=True))
 op.create_index("ix_bid_documents_classification_status","bid_documents",["classification_status"])

def downgrade():
 op.drop_index("ix_bid_documents_classification_status",table_name="bid_documents")
 for column in ["remarks","is_latest_version","classification_confidence","classification_status","document_date","revision","document_title","document_number","document_type"]:
  op.drop_column("bid_documents",column)
