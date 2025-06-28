# run with : uvicorn main:app --reload

from fastapi import FastAPI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)
import asyncio

# تنظیمات
BOT_TOKEN = "7706945625:AAFGndko0zb1ksVPPJFVfI-3JawT16GGZF0"
MANAGER_GROUP_ID = -1002760039877  # آیدی گروه مدیران با علامت منفی

app = FastAPI()

# مراحل مکالمه
FULLNAME, PHONE, BIRTHDATE, ADDRESS, RECEIPT = range(5)

user_data = {}

# استارت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("نام و نام خانوادگی :")
    return FULLNAME

async def get_fullname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id] = {"fullname": update.message.text}
    await update.message.reply_text("شماره تماس :")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id]["phone"] = update.message.text
    await update.message.reply_text("تاریخ تولد :")
    return BIRTHDATE

async def get_birthdate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id]["birthdate"] = update.message.text
    await update.message.reply_text("آدرس :")
    return ADDRESS

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id]["address"] = update.message.text
    await update.message.reply_text("تصویر فیش واریز وجه را ارسال کنید:")
    return RECEIPT

async def get_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username or ""
    user_id = update.effective_user.id
    data = user_data.get(user_id, {})

    caption = (
        f"📥  ثبت‌ نام جدید \n\n"
        f"آیدی : {user_id} \n"
        f"نام کاربری : @{username} \n\n"
        f"👤 نام: {data.get('fullname')} \n"
        f"📱 شماره تماس: {data.get('phone')} \n"
        f"🎂 تاریخ تولد: {data.get('birthdate')} \n"
        f"🏠 آدرس: {data.get('address')} \n"
        f"🧾 فیش واریزی در تصویر زیر 👇"
    )
    
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        await context.bot.send_photo(
            chat_id=MANAGER_GROUP_ID,
            photo=file_id,
            caption=caption
        )
    elif update.message.video:
        file_id = update.message.video.file_id
        await context.bot.send_video(
            chat_id=MANAGER_GROUP_ID,
            video=file_id,
            caption=caption
        )

    await update.message.reply_text("✅ ثبت‌نام شما با موفقیت انجام شد.")
    user_data.pop(user_id, None)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data.pop(update.effective_user.id, None)
    await update.message.reply_text("فرایند ثبت‌نام لغو شد.")
    return ConversationHandler.END

# تابع اجرای ربات
async def run_bot():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            FULLNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fullname)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            BIRTHDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_birthdate)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            RECEIPT: [MessageHandler(filters.PHOTO | filters.VIDEO, get_receipt)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    # توجه: عمداً stop نکردیم چون می‌خوایم همیشه فعال بمونه

# راه‌اندازی ربات هنگام استارت FastAPI
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_bot())
