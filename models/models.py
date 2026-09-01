from pydantic import BaseModel
from typing import Optional
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone, timedelta
import uuid
from config.database import Base

IST = timezone(timedelta(hours=5, minutes=30))


from typing import Optional, List, Any, Dict

class OrderRequest(BaseModel):
    item_code: Optional[str] = None
    name: Optional[str] = None
    quantity: Optional[int] = 1
    qty: Optional[int] = None
    items: Optional[List[Any]] = None
    doc: Optional[Any] = None


class TaskResponse(BaseModel):
    task_id: str
    item_code: str
    warehouse: Optional[str] = None
    rack: Optional[str] = None
    bin: Optional[str] = None
    pickup: str
    drop: str
    quantity: Optional[int] = 1
    status: str = "CREATED"


class Task(Base):
    __tablename__ = "wms_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_code = Column(String, nullable=False)
    quantity = Column(Integer, default=1)
    pickup_location = Column(String, nullable=False)
    drop_location = Column(String, nullable=False)
    status = Column(String, default="CREATED")
    # For storing in IST
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(IST)
    )
    pickup_reached_at = Column(DateTime(timezone=True), nullable=True)
    drop_started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
