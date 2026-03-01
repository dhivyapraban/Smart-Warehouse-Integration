from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class TaskCreate(BaseModel):
    item_code: str
    quantity: int
    pickup_location: str
    drop_location: str

class TaskOut(BaseModel):
    id: UUID
    item_code: str
    quantity: int
    pickup_location: str
    drop_location: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class TaskStatusUpdate(BaseModel):
    status: str
