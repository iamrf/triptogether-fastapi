from fastapi import FastAPI, HTTPException
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler
import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
import certifi

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://triptogether-beta.vercel.app/")
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB_NAME", "tourbeau")

app = FastAPI()

try:
    client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
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

class Tour(BaseModel):
    id: int
    name: str
    destination: str
    price: float
    description: Optional[str] = None

# endpointهای تلگرام
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton("📝 ثبت‌نام", web_app={"url": WEB_APP_URL})]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "برای ثبت‌نام، روی دکمه زیر یا منوی ربات کلیک کنید:",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

# تست اتصال دیتابیس
@app.get("/api/test-db")
async def test_db():
    try:
        collections = await db.list_collection_names()
        return {"status": "success", "collections": collections}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

# endpointهای کاربر
@app.post("/api/users")
async def save_user(user: UserIn):
    try:
        user_in_db = UserInDB(**user.model_dump(), created_at=datetime.utcnow())
        result = await db.users.update_one(
            {"telegram_id": user_in_db.telegram_id},
            {"$set": user_in_db.model_dump()},
            upsert=True
        )
        return {
            "status": "success",
            "message": "کاربر با موفقیت ذخیره شد",
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
            "upserted_id": str(result.upserted_id) if result.upserted_id else None
        }
    except Exception as e:
        print(f"Error in save_user: {str(e)}")
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
@app.get("/api/tours", response_model=List[Tour])
async def get_tours():
    try:
        tours = await db.tours.find().to_list(length=100)
        for tour in tours:
            tour.pop("_id", None)
        return tours
    except Exception as e:
        print(f"Error in get_tours: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get tours: {str(e)}")

@app.get("/api/tours/{id}", response_model=Tour)
async def get_tour(id: int):
    try:
        tour = await db.tours.find_one({"id": id})
        if not tour:
            raise HTTPException(status_code=404, detail="تور یافت نشد")
        tour.pop("_id", None)
        return tour
    except Exception as e:
        print(f"Error in get_tour: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get tour: {str(e)}")

async def run_bot():
    try:
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states={},
            fallbacks=[]
        )
        application.add_handler(conv_handler)
        await application.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="📝 ثبت‌نام", web_app={"url": WEB_APP_URL})
        )
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        print("Telegram bot started")
    except Exception as e:
        print(f"Error in run_bot: {str(e)}")
        raise

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_bot())

@app.get("/")
async def root():
    return {"message": "API is running"}
