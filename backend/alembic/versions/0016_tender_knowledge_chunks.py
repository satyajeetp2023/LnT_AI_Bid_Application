"""Add persistent tender knowledge chunks.

Revision ID: 0016
Revises: 0015
"""
from alembic import op
import sqlalchemy as sa

revision="0016"
down_revision="0015"
branch_labels=None
depends_on=None

def upgrade():
 op.create_table(
  "tender_knowledge_chunks",
  sa.Column("id",sa.Integer(),primary_key=True),
  sa.Column("bid_project_id",sa.Integer(),sa.ForeignKey("bid_projects.id",ondelete="CASCADE"),nullable=False),
  sa.Column("source_document_id",sa.Integer(),sa.ForeignKey("bid_documents.id",ondelete="CASCADE"),nullable=False),
  sa.Column("chunk_index",sa.Integer(),nullable=False),
  sa.Column("source_page",sa.String(50)),
  sa.Column("source_clause",sa.String(100)),
  sa.Column("source_section",sa.String(300)),
  sa.Column("text",sa.Text(),nullable=False),
  sa.Column("text_hash",sa.String(64),nullable=False),
  sa.Column("word_count",sa.Integer(),nullable=False,server_default="0"),
  sa.Column("source_kind",sa.String(60),nullable=False,server_default="Tender Document"),
  sa.Column("is_active",sa.Boolean(),nullable=False,server_default=sa.true()),
  sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
  sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
  sa.UniqueConstraint("source_document_id","chunk_index",name="uq_tender_chunk_document_index"),
 )
 for name,column in (
  ("ix_tender_knowledge_bid","bid_project_id"),
  ("ix_tender_knowledge_document","source_document_id"),
  ("ix_tender_knowledge_hash","text_hash"),
  ("ix_tender_knowledge_active","is_active"),
 ):
  op.create_index(name,"tender_knowledge_chunks",[column])

def downgrade():
 op.drop_table("tender_knowledge_chunks")
