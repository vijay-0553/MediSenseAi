import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String
from db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(120), nullable=False)
    age = Column(Integer, nullable=False, default=30)
    sex = Column(String(20), nullable=False, default="Not specified")
    contact = Column(String(50), nullable=False, default="")
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    avatar_filename = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
