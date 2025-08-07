import telebot
import json
import os

BOT_TOKEN = "8347050926:AAFOGdrN1kCyQDxpgG5orEVUXpshcPiqEyI"
CHANNEL_USERNAME = "@Luck111AvirajBhai_Bot" 
OWNER_ID = 5872702942  

bot = telebot.TeleBot(BOT_TOKEN)

USERS_FILE = "members.json"

# Load saved users
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return []

# Save user IDs
def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

# /start command: register user
@bot.message_handler(commands=['start'])
def handle_start(message):
    uid = message.from_user.id
    users = load_users()
    if uid not in users:
        users.append(uid)
        save_users(users)
    bot.reply_to(message, "✅ Welcome! You are registered for updates.")

# /broadcast command (only for you)
@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    if message.from_user.id != OWNER_ID:
        return
    text = message.text.replace("/broadcast", "", 1).strip()
    if not text:
        bot.reply_to(message, "❗ Use: /broadcast Your message here")
        return
    users = load_users()
    success = 0
    for uid in users:
        try:
            bot.send_message(uid, text)
            success += 1
        except:
            pass
    bot.reply_to(message, f"✅ Broadcast sent to {success} users.")

# Auto-approve join request
@bot.chat_join_request_handler()
def approve(req):
    if req.chat.username == CHANNEL_USERNAME.replace("@", ""):
        bot.approve_chat_join_request(req.chat.id, req.from_user.id)
        bot.send_message(req.from_user.id, "✅ You’ve been auto-approved!")
        # Save user to list
        users = load_users()
        if req.from_user.id not in users:
            users.append(req.from_user.id)
            save_users(users)

bot.infinity_polling()
