from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.db.base import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, index=True)
    user_email = Column(String)
    action = Column(String)
    detail = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
