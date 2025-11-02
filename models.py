from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, nullable=False, default=datetime.utcnow)
    tx_date = Column(Date, nullable=False)
    category = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    payer = Column(String(100), nullable=False)
    notes = Column(Text, nullable=True)
