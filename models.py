from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

# مدل‌های Pydantic
class UserBase(BaseModel):
    telegram_id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None

class User(UserBase):
    profile_photo: Optional[str] = None
    national_code: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    birthdate: Optional[datetime]
    superuser: bool = False
    created_at: datetime
    updated_at: datetime
    logins: List[datetime]
    
    class Config:
        from_attributes = True
