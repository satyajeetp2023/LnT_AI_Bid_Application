"""Add clause risk library and findings.

Revision ID: 0012
Revises: 0011
"""
from alembic import op
import sqlalchemy as sa

revision="0012"
down_revision="0011"
branch_labels=None
depends_on=None

def upgrade():
 op.create_table(
  "clause_risk_patterns",
  sa.Column("id",sa.Integer(),primary_key=True),
  sa.Column("risk_code",sa.String(80),nullable=False,unique=True),
  sa.Column("title",sa.String(300),nullable=False),
  sa.Column("category",sa.String(100),nullable=False),
  sa.Column("severity",sa.String(20),nullable=False),
  sa.Column("pattern_terms",sa.JSON(),nullable=False,server_default=sa.text("'[]'")),
  sa.Column("exclusion_terms",sa.JSON(),nullable=False,server_default=sa.text("'[]'")),
  sa.Column("explanation",sa.Text(),nullable=False),
  sa.Column("reviewer_guidance",sa.Text()),
  sa.Column("is_active",sa.Boolean(),nullable=False,server_default=sa.true()),
  sa.Column("source_type",sa.String(50),nullable=False,server_default="Firm Library"),
  sa.Column("created_by",sa.Integer(),sa.ForeignKey("users.id")),
  sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
  sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
 )
 op.create_index("ix_clause_risk_patterns_risk_code","clause_risk_patterns",["risk_code"])
 op.create_index("ix_clause_risk_patterns_category","clause_risk_patterns",["category"])
 op.create_index("ix_clause_risk_patterns_severity","clause_risk_patterns",["severity"])
 op.create_index("ix_clause_risk_patterns_is_active","clause_risk_patterns",["is_active"])

 op.create_table(
  "bid_clause_risk_findings",
  sa.Column("id",sa.Integer(),primary_key=True),
  sa.Column("bid_project_id",sa.Integer(),sa.ForeignKey("bid_projects.id",ondelete="CASCADE"),nullable=False),
  sa.Column("source_document_id",sa.Integer(),sa.ForeignKey("bid_documents.id",ondelete="CASCADE"),nullable=False),
  sa.Column("risk_pattern_id",sa.Integer(),sa.ForeignKey("clause_risk_patterns.id",ondelete="SET NULL")),
  sa.Column("risk_code",sa.String(80),nullable=False),
  sa.Column("risk_title",sa.String(300),nullable=False),
  sa.Column("risk_category",sa.String(100),nullable=False),
  sa.Column("severity",sa.String(20),nullable=False),
  sa.Column("source_page",sa.String(50)),
  sa.Column("source_clause",sa.String(100)),
  sa.Column("source_section",sa.String(300)),
  sa.Column("source_excerpt",sa.Text(),nullable=False),
  sa.Column("confidence",sa.Numeric(5,4),nullable=False),
  sa.Column("detection_method",sa.String(60),nullable=False,server_default="Firm Risk Pattern"),
  sa.Column("review_status",sa.String(40),nullable=False,server_default="Open"),
  sa.Column("reviewer_disposition",sa.String(50)),
  sa.Column("reviewer_comment",sa.Text()),
  sa.Column("reviewed_by",sa.Integer(),sa.ForeignKey("users.id")),
  sa.Column("reviewed_at",sa.DateTime(timezone=True)),
  sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
  sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
 )
 for name,column in (
  ("ix_bid_clause_risk_findings_bid","bid_project_id"),
  ("ix_bid_clause_risk_findings_document","source_document_id"),
  ("ix_bid_clause_risk_findings_pattern","risk_pattern_id"),
  ("ix_bid_clause_risk_findings_code","risk_code"),
  ("ix_bid_clause_risk_findings_category","risk_category"),
  ("ix_bid_clause_risk_findings_severity","severity"),
  ("ix_bid_clause_risk_findings_review","review_status"),
  ("ix_bid_clause_risk_findings_disposition","reviewer_disposition"),
 ):
  op.create_index(name,"bid_clause_risk_findings",[column])

def downgrade():
 op.drop_table("bid_clause_risk_findings")
 op.drop_table("clause_risk_patterns")
