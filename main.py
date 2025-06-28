# run with : uvicorn main:app --reload

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
import os
from dotenv import load_dotenv
import certifi  # اضافه کردن certifi
from trip import Trip

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB_NAME", "tourbeau")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("WEB_APP_URL")],
    allow_credentials=True,
    allow_methods="*",
    allow_headers=["*"],
)

try:
    client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())  # استفاده از certifi
    db = client[DB_NAME]
    print(f"Connected to MongoDB: {DB_NAME}")
except Exception as e:
    print(f"Failed to connect to MongoDB: {str(e)}")
    raise Exception(f"MongoDB connection error: {str(e)}")

# مدل‌های Pydantic
class UserIn(BaseModel):
    telegram_id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None

class UserInDB(UserIn):
    created_at: datetime
    updated_at: datetime


# تست اتصال دیتابیس
@app.get("/api/test-db")
async def test_db():
    try:
        collections = await db.list_collection_names()
        return {"status": 200, "collections": collections}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

# endpointهای کاربر
@app.post("/api/users")
async def save_user(user: UserIn):
    try:
        user_in_db = UserInDB(**user.model_dump(), created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        result = await db.users.update_one(
            {"telegram_id": user_in_db.telegram_id},
            {"$set": user_in_db.model_dump()},
            upsert=True
        )
        return {
            "status": 200,
            "message": "کاربر با موفقیت ذخیره شد",
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
            "upserted_id": str(result.upserted_id) if result.upserted_id else None
        }
    except Exception as e:
        print(f"Error while saving user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save user: {str(e)}")

@app.get("/api/users/{telegram_id}")
async def get_user(telegram_id: int):
    try:
        user = await db.users.find_one({"telegram_id": telegram_id})
        if not user:
            raise HTTPException(status_code=404, detail="کاربر یافت نشد")
        user.pop("_id", None)
        return user
    except Exception as e:
        print(f"Error in get_user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user: {str(e)}")

# endpointهای تورها
@app.get("/api/trips", response_model=List[Trip])
async def get_trips():
    try:
        trips = await db.trips.find().to_list(length=100)
        for trip in trips:
            trip.pop("_id", None)
        return trips
    except Exception as e:
        print(f"Error in get_trips: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get trips: {str(e)}")

@app.get("/api/trips/{id}", response_model=Trip)
async def get_trip(id: int):
    try:
        trip = await db.trips.find_one({"id": id})
        if not trip:
            raise HTTPException(status_code=404, detail="تور یافت نشد")
        trip.pop("_id", None)
        return trip
    except Exception as e:
        print(f"Error in get_trip: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get trip: {str(e)}")

@app.get("/")
async def root():
    return {"message": "API is running"}
