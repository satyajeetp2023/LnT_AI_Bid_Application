from datetime import date,datetime,timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint,Date,DateTime,ForeignKey,Integer,Numeric,String,Text
from sqlalchemy.orm import Mapped,mapped_column

from app.database.session import Base


def now():return datetime.now(timezone.utc)


class ExecutionOutcome(Base):
 __tablename__="execution_outcomes"
 __table_args__=(
  CheckConstraint("execution_status IN ('Not Started','In Progress','Completed','Closed')",name="ck_execution_status"),
  CheckConstraint("review_status IN ('Draft','Reviewed')",name="ck_execution_review_status"),
  CheckConstraint("final_contract_value IS NULL OR final_contract_value >= 0",name="ck_execution_final_value"),
  CheckConstraint("actual_cost IS NULL OR actual_cost >= 0",name="ck_execution_actual_cost"),
  CheckConstraint("final_margin_percent IS NULL OR (final_margin_percent >= -100 AND final_margin_percent <= 100)",name="ck_execution_margin"),
  CheckConstraint("approved_variations IS NULL OR approved_variations >= 0",name="ck_execution_variations"),
  CheckConstraint("claims_recovered IS NULL OR claims_recovered >= 0",name="ck_execution_claims"),
  CheckConstraint("eot_days IS NULL OR eot_days >= 0",name="ck_execution_eot"),
  CheckConstraint("actual_completion_date IS NULL OR actual_start_date IS NULL OR actual_completion_date >= actual_start_date",name="ck_execution_dates"),
 )
 id:Mapped[int]=mapped_column(primary_key=True)
 bid_project_id:Mapped[int]=mapped_column(ForeignKey("bid_projects.id",ondelete="CASCADE"),unique=True,index=True)
 execution_status:Mapped[str]=mapped_column(String(30),default="Not Started",index=True)
 data_date:Mapped[date|None]=mapped_column(Date,index=True)
 actual_start_date:Mapped[date|None]=mapped_column(Date)
 actual_completion_date:Mapped[date|None]=mapped_column(Date)
 final_contract_value:Mapped[Decimal|None]=mapped_column(Numeric(18,2))
 actual_cost:Mapped[Decimal|None]=mapped_column(Numeric(18,2))
 final_margin_percent:Mapped[Decimal|None]=mapped_column(Numeric(7,3))
 approved_variations:Mapped[Decimal|None]=mapped_column(Numeric(18,2))
 claims_recovered:Mapped[Decimal|None]=mapped_column(Numeric(18,2))
 eot_days:Mapped[int|None]=mapped_column(Integer)
 source_reference:Mapped[str|None]=mapped_column(String(500))
 notes:Mapped[str|None]=mapped_column(Text)
 review_status:Mapped[str]=mapped_column(String(20),default="Draft",index=True)
 reviewed_by:Mapped[int|None]=mapped_column(ForeignKey("users.id"))
 reviewed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
 created_by:Mapped[int]=mapped_column(ForeignKey("users.id"))
 updated_by:Mapped[int|None]=mapped_column(ForeignKey("users.id"))
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
 updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)


class ExecutionLearningFactor(Base):
 __tablename__="execution_learning_factors"
 __table_args__=(
  CheckConstraint("impact_area IN ('Cost','Time','Margin','Revenue','Productivity','Scope','Mixed')",name="ck_execution_factor_area"),
  CheckConstraint("direction IN ('Adverse','Favorable','Neutral')",name="ck_execution_factor_direction"),
  CheckConstraint("review_status IN ('Draft','Reviewed')",name="ck_execution_factor_review"),
  CheckConstraint("quantified_impact IS NULL OR quantified_impact >= 0",name="ck_execution_factor_impact"),
 )
 id:Mapped[int]=mapped_column(primary_key=True)
 bid_project_id:Mapped[int]=mapped_column(ForeignKey("bid_projects.id",ondelete="CASCADE"),index=True)
 execution_outcome_id:Mapped[int]=mapped_column(ForeignKey("execution_outcomes.id",ondelete="CASCADE"),index=True)
 factor_category:Mapped[str]=mapped_column(String(80),index=True)
 impact_area:Mapped[str]=mapped_column(String(30),index=True)
 direction:Mapped[str]=mapped_column(String(20),index=True)
 title:Mapped[str]=mapped_column(String(300))
 description:Mapped[str]=mapped_column(Text)
 quantified_impact:Mapped[Decimal|None]=mapped_column(Numeric(18,3))
 impact_unit:Mapped[str|None]=mapped_column(String(40))
 source_reference:Mapped[str|None]=mapped_column(String(500))
 source_excerpt:Mapped[str|None]=mapped_column(Text)
 lesson_for_future_bids:Mapped[str|None]=mapped_column(Text)
 review_status:Mapped[str]=mapped_column(String(20),default="Draft",index=True)
 reviewed_by:Mapped[int|None]=mapped_column(ForeignKey("users.id"))
 reviewed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
 created_by:Mapped[int]=mapped_column(ForeignKey("users.id"))
 updated_by:Mapped[int|None]=mapped_column(ForeignKey("users.id"))
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
 updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)
