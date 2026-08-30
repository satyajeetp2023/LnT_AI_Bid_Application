"""Add drawing quantity and BOQ verification.

Revision ID: 0014
Revises: 0013
"""
from alembic import op
import sqlalchemy as sa

revision="0014"
down_revision="0013"
branch_labels=None
depends_on=None

def upgrade():
 op.create_table(
  "drawing_quantity_observations",
  sa.Column("id",sa.Integer(),primary_key=True),
  sa.Column("bid_project_id",sa.Integer(),sa.ForeignKey("bid_projects.id",ondelete="CASCADE"),nullable=False),
  sa.Column("source_document_id",sa.Integer(),sa.ForeignKey("bid_documents.id",ondelete="CASCADE"),nullable=False),
  sa.Column("source_page",sa.String(50)),
  sa.Column("drawing_reference",sa.String(200)),
  sa.Column("item_name",sa.String(300),nullable=False),
  sa.Column("item_category",sa.String(100)),
  sa.Column("quantity",sa.Numeric(18,6),nullable=False),
  sa.Column("unit",sa.String(50),nullable=False),
  sa.Column("evidence_text",sa.Text()),
  sa.Column("evidence_region",sa.JSON()),
  sa.Column("extraction_method",sa.String(60),nullable=False,server_default="Vision Extraction"),
  sa.Column("extraction_confidence",sa.Numeric(5,4),nullable=False),
  sa.Column("review_status",sa.String(40),nullable=False,server_default="Needs Review"),
  sa.Column("reviewer_comment",sa.Text()),
  sa.Column("reviewed_by",sa.Integer(),sa.ForeignKey("users.id")),
  sa.Column("reviewed_at",sa.DateTime(timezone=True)),
  sa.Column("created_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
  sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
  sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
 )
 for name,column in (
  ("ix_drawing_qty_bid","bid_project_id"),("ix_drawing_qty_document","source_document_id"),
  ("ix_drawing_qty_reference","drawing_reference"),("ix_drawing_qty_item","item_name"),
  ("ix_drawing_qty_category","item_category"),("ix_drawing_qty_unit","unit"),("ix_drawing_qty_review","review_status"),
 ):
  op.create_index(name,"drawing_quantity_observations",[column])

 op.create_table(
  "drawing_boq_findings",
  sa.Column("id",sa.Integer(),primary_key=True),
  sa.Column("bid_project_id",sa.Integer(),sa.ForeignKey("bid_projects.id",ondelete="CASCADE"),nullable=False),
  sa.Column("observation_id",sa.Integer(),sa.ForeignKey("drawing_quantity_observations.id",ondelete="CASCADE"),nullable=False),
  sa.Column("boq_scope_item_id",sa.Integer(),sa.ForeignKey("schedule_scope_items.id",ondelete="SET NULL")),
  sa.Column("match_confidence",sa.Numeric(5,4),nullable=False),
  sa.Column("boq_reference",sa.String(200)),
  sa.Column("boq_description",sa.String(500)),
  sa.Column("boq_quantity",sa.Numeric(18,6)),
  sa.Column("boq_unit",sa.String(50)),
  sa.Column("drawing_quantity",sa.Numeric(18,6),nullable=False),
  sa.Column("drawing_unit",sa.String(50),nullable=False),
  sa.Column("variance_quantity",sa.Numeric(18,6)),
  sa.Column("variance_percent",sa.Numeric(18,6)),
  sa.Column("finding_status",sa.String(50),nullable=False),
  sa.Column("review_status",sa.String(40),nullable=False,server_default="Open"),
  sa.Column("reviewer_disposition",sa.String(60)),
  sa.Column("reviewer_comment",sa.Text()),
  sa.Column("reviewed_by",sa.Integer(),sa.ForeignKey("users.id")),
  sa.Column("reviewed_at",sa.DateTime(timezone=True)),
  sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
  sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
 )
 for name,column in (
  ("ix_drawing_boq_bid","bid_project_id"),("ix_drawing_boq_observation","observation_id"),
  ("ix_drawing_boq_scope","boq_scope_item_id"),("ix_drawing_boq_status","finding_status"),
  ("ix_drawing_boq_review","review_status"),
 ):
  op.create_index(name,"drawing_boq_findings",[column])

def downgrade():
 op.drop_table("drawing_boq_findings")
 op.drop_table("drawing_quantity_observations")
