from sqlalchemy import Column, Integer, String, Date, UniqueConstraint
from app.db.base import Base

class Store(Base):
    __tablename__ = "stores"
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, index=True)
    store_id = Column(String, index=True)
    store_name = Column(String)
    priority = Column(Integer, default=1)
    __table_args__ = (UniqueConstraint('org_id','store_id', name='uq_org_store'),)

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, index=True)
    sku = Column(String, index=True)
    style = Column(String)
    size = Column(String)
    category = Column(String)

class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, index=True)
    date = Column(Date, index=True)
    store_id = Column(String, index=True)
    store_name = Column(String)
    sku = Column(String, index=True)
    style = Column(String)
    size = Column(String)
    units_sold = Column(Integer)

class Stock(Base):
    __tablename__ = "stock"
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, index=True)
    store_id = Column(String, index=True)
    store_name = Column(String)
    sku = Column(String, index=True)
    style = Column(String)
    size = Column(String)
    on_hand = Column(Integer, default=0)

class Rules(Base):
    __tablename__ = "rules"
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, index=True)
    target_days_cover = Column(Integer, default=7)
    min_display = Column(Integer, default=1)
    pack_size = Column(Integer, default=1)
