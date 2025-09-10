from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class TransferPlan(Base):
    __tablename__ = "transfer_plans"
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, index=True)
    created_by = Column(Integer, index=True)
    status = Column(String, default="Draft")
    lookback_days = Column(Integer, default=7)
    created_at = Column(DateTime, default=datetime.utcnow)
    items = relationship("TransferItem", back_populates="plan")

class TransferItem(Base):
    __tablename__ = "transfer_items"
    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("transfer_plans.id"))
    from_store_id = Column(String)
    from_store = Column(String)
    to_store_id = Column(String)
    to_store = Column(String)
    sku = Column(String)
    style = Column(String)
    size = Column(String)
    qty = Column(Integer)
    plan = relationship("TransferPlan", back_populates="items")

class PlanComment(Base):
    __tablename__ = "plan_comments"
    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, index=True)
    user_email = Column(String)
    comment = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
