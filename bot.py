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

    if not message.reply_to_message:
        bot.reply_to(message, "❗Please reply to a message to broadcast (text, image, video, etc.)")
        return

    user_ids = load_users()
    content = message.reply_to_message
    sent_count = 0

    for uid in user_ids:
        try:
            if content.text:
                bot.send_message(uid, content.text)
            elif content.photo:
                bot.send_photo(uid, content.photo[-1].file_id, caption=content.caption or "")
            elif content.video:
                bot.send_video(uid, content.video.file_id, caption=content.caption or "")
            elif content.voice:
                bot.send_voice(uid, content.voice.file_id, caption=content.caption or "")
            elif content.audio:
                bot.send_audio(uid, content.audio.file_id, caption=content.caption or "")
            elif content.document:
                bot.send_document(uid, content.document.file_id, caption=content.caption or "")
            elif content.sticker:
                bot.send_sticker(uid, content.sticker.file_id)
            else:
                continue

            sent_count += 1

        except Exception as e:
            print(f"❌ Failed to send to {uid}: {e}")
            continue

    bot.reply_to(message, f"✅ Broadcast sent to {sent_count} users.")
def load_users():
    with open("users.txt", "r") as f:
        return [int(line.strip()) for line in f if line.strip().isdigit()]

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
