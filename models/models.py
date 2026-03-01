from pydantic import BaseModel
from typing import Optional
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from config.database import Base


class OrderRequest(BaseModel):
    item_code: str
    quantity: Optional[int] = 1


class TaskResponse(BaseModel):
    task_id: str
    item_code: str
    pickup: str
    drop: str
    status: str


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_code = Column(String, nullable=False)
    quantity = Column(Integer, default=1)
    pickup_location = Column(String, nullable=False)
    drop_location = Column(String, nullable=False)
    status = Column(String, default="CREATED")
    created_at = Column(DateTime, default=datetime.utcnow)
    pickup_reached_at = Column(DateTime, nullable=True)
    drop_started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
