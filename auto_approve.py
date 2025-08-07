from telegram import Update
from telegram.ext import ApplicationBuilder, ChatJoinRequestHandler, ContextTypes
import os

BOT_TOKEN = os.environ['8347050926:AAFOGdrN1kCyQDxpgG5orEVUXpshcPiqEyI']
CHANNEL_USERNAME = os.environ.get("@Luck111AvirajBhai_Bot")

async def approve_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.chat_join_request.approve()
    print(f"✅ Approved: {update.chat_join_request.from_user.id}")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(ChatJoinRequestHandler(approve_join))
app.run_polling()
