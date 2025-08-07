import telebot
import threading

BOT_TOKEN = "8347050926:AAFOGdrN1kCyQDxpgG5orEVUXpshcPiqEyI"
bot = telebot.TeleBot(BOT_TOKEN)

ADMIN_ID = 5872702942  # admin ID bina quotes

@bot.chat_join_request_handler()
def approve_request(join_request):
    chat_id = join_request.chat.id
    user_id = join_request.from_user.id
    bot.approve_chat_join_request(chat_id, user_id)
    bot.send_message(user_id, "✅ Welcome to the channel!")

@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text.replace("/broadcast ", "")
    user_ids = load_users()
    for uid in user_ids:
        try:
            bot.send_message(uid, text)
        except:
            continue

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
