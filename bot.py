import telebot
from flask import Flask, request

BOT_TOKEN = '8347050926:AAFOGdrN1kCyQDxpgG5orEVUXpshcPiqEyI'
ADMIN_ID = 5872702942

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(_name_)
user_file = 'users.txt'

# ✅ Save and Load User IDs
def save_user(user_id):
    with open(user_file, "a+") as f:
        f.seek(0)
        users = f.read().splitlines()
        if str(user_id) not in users:
            f.write(f"{user_id}\n")

def load_users():
    try:
        with open(user_file, "r") as f:
            return list(set(int(line.strip()) for line in f if line.strip()))
    except:
        return []

# ✅ Start command
@bot.message_handler(commands=['start'])
def start(message):
    save_user(message.chat.id)
    bot.send_message(message.chat.id, "👋 Welcome! You will get updates here.")

# ✅ Broadcast
@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text.replace("/broadcast", "").strip()
    user_ids = load_users()
    sent = 0
    for uid in user_ids:
        try:
            bot.send_message(uid, text)
            sent += 1
        except:
            continue
    bot.send_message(message.chat.id, f"✅ Sent to {sent} users.")

# ✅ Auto-approval of join requests
@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    if update.chat_join_request:
        bot.approve_chat_join_request(
            update.chat_join_request.chat.id,
            update.chat_join_request.from_user.id
        )
        bot.send_message(update.chat_join_request.from_user.id, "✅ Welcome to the channel!")
    else:
        bot.process_new_updates([update])
    return 'ok', 200

# ✅ Root check
@app.route('/')
def index():
    return "Bot running!", 200

# ✅ Run Flask
if _name_ == "_main_":
    app.run(host="0.0.0.0", port=8080)
