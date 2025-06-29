# run with : uvicorn main:app --reload

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from typing import List
import os
import requests
from dotenv import load_dotenv
import certifi  # اضافه کردن certifi
from models import User, UserBase
from trip import Trip

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB_NAME", "tourbeau")
WEB_APP_URL = os.getenv("WEB_APP_URL")
TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[WEB_APP_URL] if WEB_APP_URL else ["*"],
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


# تست اتصال دیتابیس
@app.get("/api/test-db")
async def test_db():
    try:
        collections = await db.list_collection_names()
        return {"status": 200, "collections": collections}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

async def get_telegram_profile_photo(telegram_id: int) -> str | None:
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUserProfilePhotos"
        params = {"user_id": telegram_id, "limit": 1}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("ok") and data["result"]["total_count"] > 0:
            photo = data["result"]["photos"][0][0]
            file_id = photo["file_id"]
            file_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
            file_response = requests.get(file_url)
            file_response.raise_for_status()
            file_data = file_response.json()
            if file_data.get("ok"):
                file_path = file_data["result"]["file_path"]
                return f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        return None
    except Exception as e:
        return None

# endpointهای کاربر
@app.post("/api/users", response_model=User)
async def save_user(user: UserBase):
    try:
        current_time = datetime.utcnow()
        existing_user = await db.users.find_one({"telegram_id": user.telegram_id})
        if existing_user:
            update_data = {
                "$set":{
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "username": user.username,
                    "updated_at": current_time,
                },
                "$push": {
                    "logins": current_time
                }
            }
            profile_photo = await get_telegram_profile_photo(user.telegram_id)
            if profile_photo:
                update_data["$set"]["profile_photo"] = profile_photo
            
            result = await db.users.update_one(
                {"telegram_id": user.telegram_id},
                update_data
            )
            if result.modified_count or result.matched_count:
                return await db.users.find_one({"telegram_id": user.telegram_id})
            raise HTTPException(status_code=500, detail="Failed to update user")

        profile_photo = await get_telegram_profile_photo(user.telegram_id)

        user_in_db = User(**user.model_dump(),profile_photo=profile_photo, logins=[current_time] ,created_at=current_time, updated_at=current_time)
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
