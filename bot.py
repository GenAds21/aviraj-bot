# bot.py — Final (SQLite persistent + auto-approve + safe broadcast)
import telebot
import sqlite3
import threading
import time
import random
import re
from telebot import apihelper

# ---------------- CONFIG ----------------
BOT_TOKEN = "8347050926:AAFOGdrN1kCyQDxpgG5orEVUXpshcPiqEyI"   # <- your bot token
ADMIN_ID = 5872702942                                         # <- your Telegram numeric ID (owner only)
DB_FILE = "users.db"
MIN_DELAY = 0.5    # minimum seconds between messages
MAX_DELAY = 1.2    # maximum seconds between messages
RETRY_WAIT_EXTRA = 1  # extra seconds after Telegram's retry-after
# ----------------------------------------

bot = telebot.TeleBot(BOT_TOKEN)

# ---------- SQLite helpers ----------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY
                )""")
    conn.commit()
    conn.close()

def add_user(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (int(user_id),))
        conn.commit()
    except Exception as e:
        print("DB add_user error:", e)
    finally:
        conn.close()

def remove_user(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("DELETE FROM users WHERE user_id = ?", (int(user_id),))
        conn.commit()
    except Exception as e:
        print("DB remove_user error:", e)
    finally:
        conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

# initialize DB
init_db()

# ---------- Helpers for safe sending ----------
def parse_retry_after(err_text: str):
    """Try to extract retry-after seconds from Telegram error text."""
    # error text often contains: "Too Many Requests: retry after X"
    m = re.search(r"retry after (\d+)", err_text, re.IGNORECASE)
    if m:
        try:
            return int(m.group(1))
        except:
            return None
    return None

def safe_send(send_func, *args, **kwargs):
    """
    send_func: bot.send_message / send_photo / send_video / ...
    returns True if sent, False if failed (and removed)
    Handles Api exceptions like FloodWait and Forbidden (block).
    """
    max_retries = 3
    attempt = 0
    while attempt < max_retries:
        try:
            send_func(*args, **kwargs)
            return True
        except apihelper.ApiTelegramException as e:
            text = str(e)
            # FloodWait (Too Many Requests)
            retry_after = parse_retry_after(text)
            if retry_after:
                wait = retry_after + RETRY_WAIT_EXTRA
                print(f"[safe_send] FloodWait detected. Sleeping {wait}s (attempt {attempt+1})")
                time.sleep(wait)
                attempt += 1
                continue
            # Forbidden or blocked by user — remove user
            if "bot was blocked" in text.lower() or "forbidden" in text.lower() or "user is deactivated" in text.lower():
                print(f"[safe_send] User blocked or forbidden: {text}")
                # caller should remove user
                return False
            # other api errors: break/skip
            print(f"[safe_send] ApiTelegramException (non-flood): {text}")
            return False
        except Exception as ex:
            # network/other error — wait a bit and retry
            print(f"[safe_send] Exception: {ex} (attempt {attempt+1})")
            time.sleep(1 + attempt)
            attempt += 1
    return False

def random_delay():
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

# ---------------- Handlers ----------------

# /start — register user (persistent)
@bot.message_handler(commands=['start'])
def handle_start(message):
    uid = message.from_user.id
    add_user(uid)
    try:
        bot.reply_to(message, "✅ You are registered for broadcasts.")
    except Exception as e:
        print("Reply failed:", e)

# Auto-approve join requests for private channels/groups
@bot.chat_join_request_handler()
def approve_request(join_request):
    """
    join_request has: chat.id (channel), from_user.id
    Approves the join request, adds the user to DB, optionally DM welcome.
    """
    try:
        # Approve (bot must be channel admin with approve permission)
        bot.approve_chat_join_request(join_request.chat.id, join_request.from_user.id)
        add_user(join_request.from_user.id)
        # Try send welcome DM (may fail if user blocked)
        try:
            bot.send_message(join_request.from_user.id, "✅ Your request is approved. Welcome to the channel!")
        except Exception:
            pass
        print("Approved and added:", join_request.from_user.id)
    except Exception as e:
        print("approve_request error:", e)

# Universal broadcast:
# - Reply to a content message with /broadcast -> sends that content
# - Or /broadcast your text -> sends text
@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return

    users = get_all_users()
    if not users:
        bot.reply_to(message, "⚠ No users to broadcast to.")
        return

    reply = message.reply_to_message
    sent = 0
    removed = 0
    failed = 0

    # helper to send and handle removal on block
    def send_and_handle(uid, func, *fargs, **fkwargs):
        nonlocal sent, removed, failed
        ok = safe_send(func, *fargs, **fkwargs)
        if ok:
            sent += 1
            random_delay()
        else:
            # if failed due to block/forbidden, remove user
            # safe_send returns False for both block and other failures — check with one attempt to see if forbidden
            # We'll attempt a direct check: try a simple send_message to test forbidden reason
            try:
                bot.send_chat_action(uid, 'typing')  # quick check (may also throw)
                # If no exception but previous send failed, count as failed (not removed)
                failed += 1
                random_delay()
            except apihelper.ApiTelegramException as e2:
                txt = str(e2).lower()
                if "bot was blocked" in txt or "forbidden" in txt or "user is deactivated" in txt:
                    remove_user(uid)
                    removed += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

    try:
        if reply:
            # Media: prefer in this order (works for common types)
            # PHOTO
            if reply.photo:
                file_id = reply.photo[-1].file_id
                caption = reply.caption or ""
                for uid in users:
                    send_and_handle(uid, bot.send_photo, uid, file_id, caption=caption)

            # VIDEO
            elif reply.video:
                file_id = reply.video.file_id
                caption = reply.caption or ""
                for uid in users:
                    send_and_handle(uid, bot.send_video, uid, file_id, caption=caption)

            # VOICE
            elif reply.voice:
                file_id = reply.voice.file_id
                for uid in users:
                    send_and_handle(uid, bot.send_voice, uid, file_id)

            # AUDIO (mp3)
            elif reply.audio:
                file_id = reply.audio.file_id
                caption = reply.caption or ""
                for uid in users:
                    send_and_handle(uid, bot.send_audio, uid, file_id, caption=caption)

            # DOCUMENT (pdf, zip, etc.)
            elif reply.document:
                file_id = reply.document.file_id
                caption = reply.caption or ""
                for uid in users:
                    send_and_handle(uid, bot.send_document, uid, file_id, caption=caption)

            # STICKER
            elif reply.sticker:
                file_id = reply.sticker.file_id
                for uid in users:
                    send_and_handle(uid, bot.send_sticker, uid, file_id)

            # TEXT / CAPTION
            elif reply.text:
                text = reply.text
                for uid in users:
                    send_and_handle(uid, bot.send_message, uid, text)

            else:
                bot.reply_to(message, "⚠ Unsupported reply type.")
                return

        else:
            # direct text after /broadcast
            text = message.text.replace("/broadcast", "", 1).strip()
            if not text:
                bot.reply_to(message, "⚠ Please reply to a message or send: /broadcast Your message here")
                return
            for uid in users:
                send_and_handle(uid, bot.send_message, uid, text)

        bot.reply_to(message, f"✅ Broadcast finished. Sent: {sent}  Removed: {removed}  Failed: {failed}")

    except Exception as e:
        print("Broadcast exception:", e)
        bot.reply_to(message, f"❌ Broadcast error: {e}")

# Extra: Admin command to count users
@bot.message_handler(commands=['count'])
def count_cmd(m):
    if m.from_user.id != ADMIN_ID:
        return
    users = get_all_users()
    bot.reply_to(m, f"Total users in DB: {len(users)}")

# Start polling in a thread (works on Railway with threading trick)
def run_polling():
    print("Starting bot polling...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)

if _name_ == "_main_":
    t = threading.Thread(target=run_polling, daemon=True)
    t.start()
    # keep main process alive
    while True:
        time.sleep(60)
