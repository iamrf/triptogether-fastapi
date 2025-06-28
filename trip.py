from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class TripBase(BaseModel):
    title: str
    description: str
    startDate: datetime = None
    endDate: datetime = None
    destination: str = None
    price: int = 0
    category: str = None
    image: str = None
    options: list[str] = []
    capacity: int = 0
    availableSlots: int = 0

class Trip(TripBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
