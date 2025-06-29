# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from models import User, UserCreate, Tour, TourCreate
from typing import List
import os
from dotenv import load_dotenv
import requests
from datetime import datetime
import certifi
import logging

load_dotenv()

app = FastAPI()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB_NAME", "tourbeau")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEB_APP_URL = os.getenv("WEB_APP_URL")

if not WEB_APP_URL:
    raise ValueError("WEB_APP_URL environment variable is required")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[WEB_APP_URL.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
db = client[DB_NAME]

async def get_telegram_profile_photo(telegram_id: int) -> str | None:
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUserProfilePhotos"
        params = {"user_id": telegram_id, "limit": 1}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("ok") and data["result"]["total_count"] > 0:
            photo = data["result"]["photos"][0][-1]  # بالاترین کیفیت
            file_id = photo["file_id"]
            file_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
            file_response = requests.get(file_url)
            file_response.raise_for_status()
            file_data = file_response.json()
            if file_data.get("ok"):
                file_path = file_data["result"]["file_path"]
                return f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        return None
    except Exception as e:
        return None

@app.post("/api/save-user")
async def save_user(user: UserCreate):
    try:
        current_time = datetime.utcnow()
        existing_user = await db.users.find_one({"telegram_id": user.telegram_id})
        
        if existing_user:
            # کاربر وجود داره، فقط updated_at, logins و profile_photo رو به‌روزرسانی کن
            update_data = {
                "$set": {
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
                updated_user = await db.users.find_one({"telegram_id": user.telegram_id})
                updated_user.pop("_id", None)
                return {
                    "status": 200,
                    "message": "کاربر با موفقیت به‌روزرسانی شد",
                    "matched_count": result.matched_count,
                    "modified_count": result.modified_count,
                    "upserted_id": str(result.upserted_id) if result.upserted_id else None,
                    "user": updated_user
                }
            raise HTTPException(status_code=500, detail="Failed to update user")
        
        # کاربر جدید
        profile_photo = await get_telegram_profile_photo(user.telegram_id)
        user_dict = user.dict()
        user_dict["profile_photo"] = profile_photo
        user_dict["created_at"] = current_time
        user_dict["updated_at"] = current_time
        user_dict["logins"] = [current_time]
        user_dict["id"] = (await db.users.count_documents({})) + 1
        
        result = await db.users.insert_one(user_dict)
        if result.inserted_id:
            new_user = await db.users.find_one({"_id": result.inserted_id})
            new_user.pop("_id", None)
            return {
                "status": 200,
                "message": "کاربر با موفقیت ذخیره شد",
                "matched_count": 0,
                "modified_count": 0,
                "upserted_id": str(result.inserted_id),
                "user": new_user
            }
        raise HTTPException(status_code=500, detail="Failed to save user")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving user: {str(e)}")

@app.get("/api/users/{telegram_id}")
async def get_user(telegram_id: int):
    try:
        user = await db.users.find_one({"telegram_id": telegram_id})
        if not user:
            raise HTTPException(status_code=404, detail="کاربر یافت نشد")
        user.pop("_id", None)
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user: {str(e)}")

# endpointهای تورها
@app.get("/api/trips", response_model=List[Tour])
async def get_trips():
    try:
        trips = await db.trips.find().to_list(length=100)
        for trip in trips:
            trip.pop("_id", None)
        return trips
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trips: {str(e)}")

@app.get("/api/trips/{id}", response_model=Tour)
async def get_trip(id: int):
    try:
        trip = await db.trips.find_one({"id": id})
        if not trip:
            raise HTTPException(status_code=404, detail="تور یافت نشد")
        trip.pop("_id", None)
        return trip
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trip: {str(e)}")

@app.get("/")
async def root():
    return {"message": "API is running"}