import telebot
import threading

BOT_TOKEN = "8347050926:AAFOGdrN1kCyQDxpgG5orEVUXpshcPiqEyI"
bot = telebot.TeleBot(BOT_TOKEN)

ADMIN_ID = 5872702942  # admin ID bina quotes

# ✅ Auto-Approve Join Requests
@bot.chat_join_request_handler()
def approve_request(join_request):
    chat_id = join_request.chat.id
    user_id = join_request.from_user.id
    bot.approve_chat_join_request(chat_id, user_id)
    save_user(user_id)  # 👈 Yeh line add karni hai
    bot.send_message(user_id, "Bhai Apka Joining Request Accept Kar liya ✅ 🥳 अब चैनल से रोज खेलो और PROFIT बनाओ 🤑!")

from telebot import types

@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return

    user_ids = load_users()

    # Case 1: Reply to a photo (with or without caption)
    if message.reply_to_message and message.reply_to_message.photo:
        caption = message.reply_to_message.caption or ""
        photo_file_id = message.reply_to_message.photo[-1].file_id
        for uid in user_ids:
            try:
                bot.send_photo(uid, photo_file_id, caption=caption)
            except Exception as e:
                print(f"❌ Failed to send photo to {uid}: {e}")
        bot.reply_to(message, "✅ Photo broadcast sent.")

    # Case 2: Reply to a text message
    elif message.reply_to_message and message.reply_to_message.text:
        text = message.reply_to_message.text
        for uid in user_ids:
            try:
                bot.send_message(uid, text)
            except Exception as e:
                print(f"❌ Failed to send message to {uid}: {e}")
        bot.reply_to(message, "✅ Text broadcast sent.")

    # Case 3: No reply — Use text after /broadcast command
    else:
        text = message.text.replace("/broadcast", "").strip()
        if not text:
            bot.reply_to(message, "⚠ Please send /broadcast with a message or reply to a photo/text.")
            return

        for uid in user_ids:
            try:
                bot.send_message(uid, text)
            except Exception as e:
                print(f"❌ Failed to send message to {uid}: {e}")
        bot.reply_to(message, "✅ Text broadcast sent.")

@bot.message_handler(commands=['start'])
def start(message):
    save_user(message.chat.id)
    bot.send_message(message.chat.id, "👋 Welcome! You will get updates here.")

def save_user(user_id):
    with open("users.txt", "a") as f:
        f.write(f"{user_id}\n")

def load_users():
    try:
        with open("users.txt", "r") as f:
            return list(set(int(line.strip()) for line in f if line.strip()))
    except:
        return []

# ✅ Start the bot in a thread to avoid async error
def run_bot():
    bot.polling(none_stop=True)

threading.Thread(target=run_bot).start()
