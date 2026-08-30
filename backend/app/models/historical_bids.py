from datetime import date,datetime,timezone
from decimal import Decimal

from sqlalchemy import Boolean,Date,DateTime,ForeignKey,Numeric,String,Text,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column

from app.database.session import Base


def now():return datetime.now(timezone.utc)


class BidOutcome(Base):
 __tablename__="bid_outcomes"
 id:Mapped[int]=mapped_column(primary_key=True)
 bid_project_id:Mapped[int]=mapped_column(ForeignKey("bid_projects.id",ondelete="CASCADE"),unique=True,index=True)
 result_status:Mapped[str]=mapped_column(String(40),default="Pending",index=True)
 result_date:Mapped[date|None]=mapped_column(Date)
 our_rank:Mapped[int|None]=mapped_column()
 our_bid_value:Mapped[Decimal|None]=mapped_column(Numeric(18,2))
 our_margin_percent:Mapped[Decimal|None]=mapped_column(Numeric(7,3))
 awarded_bidder:Mapped[str|None]=mapped_column(String(200))
 win_reason:Mapped[str|None]=mapped_column(Text)
 loss_reason:Mapped[str|None]=mapped_column(Text)
 source_reference:Mapped[str|None]=mapped_column(String(500))
 notes:Mapped[str|None]=mapped_column(Text)
 created_by:Mapped[int]=mapped_column(ForeignKey("users.id"))
 updated_by:Mapped[int|None]=mapped_column(ForeignKey("users.id"))
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
 updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)


class BidPriceRecord(Base):
 __tablename__="bid_price_records"
 __table_args__=(
  UniqueConstraint("bid_project_id","rank",name="uq_bid_price_rank"),
  UniqueConstraint("bid_project_id","bidder_name",name="uq_bid_price_bidder"),
 )
 id:Mapped[int]=mapped_column(primary_key=True)
 bid_project_id:Mapped[int]=mapped_column(ForeignKey("bid_projects.id",ondelete="CASCADE"),index=True)
 bidder_name:Mapped[str]=mapped_column(String(200),index=True)
 rank:Mapped[int]=mapped_column(index=True)
 bid_value:Mapped[Decimal]=mapped_column(Numeric(18,2))
 currency:Mapped[str]=mapped_column(String(3),default="INR")
 is_ours:Mapped[bool]=mapped_column(Boolean,default=False,index=True)
 source_reference:Mapped[str|None]=mapped_column(String(500))
 created_by:Mapped[int]=mapped_column(ForeignKey("users.id"))
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
