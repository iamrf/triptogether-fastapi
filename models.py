# models.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class UserBase(BaseModel):
    telegram_id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None

class UserCreate(UserBase):
    profile_photo: Optional[str] = None

class User(UserBase):
    id: int
    profile_photo: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    logins: List[datetime]

    class Config:
        from_attributes = True

# models/tour.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class Category(BaseModel):
    title: str
    href: str

class TourBase(BaseModel):
    title: str
    description: str
    startDate: str
    endDate: str
    destination: str
    price: int
    category: Category
    imageUrl: str
    options: str
    capacity: int
    availableSlots: int

class TourCreate(TourBase):
    pass

class Tour(TourBase):
    id: int
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True