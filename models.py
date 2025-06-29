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
    created_at: datetime
    updated_at: datetime
    logins: List[datetime]
    
    class Config:
        from_attributes = True
