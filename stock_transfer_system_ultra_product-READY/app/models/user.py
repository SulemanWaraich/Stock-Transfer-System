from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)
    logo_url = Column(String, nullable=True)
    users = relationship("User", back_populates="org")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="Viewer")
    org_id = Column(Integer, ForeignKey("organizations.id"))
    org = relationship("Organization", back_populates="users")
    created_at = Column(DateTime, default=datetime.utcnow)
