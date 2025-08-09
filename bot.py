# bot.py (crash-resistant final)
import telebot
from telebot import apihelper
import sqlite3
import threading
import time
import random
import json
import os
import re
import traceback
import sys

# ========== CONFIG ==========
BOT_TOKEN = "8347050926:AAFOGdrN1kCyQDxpgG5orEVUXpshcPiqEyI"   # <- PUT NEW TOKEN HERE (do not share publicly)
ADMIN_ID = 5872702942                       # <- your numeric Telegram ID
DB_FILE = "users.db"
JSON_BACKUP = "users_backup.json"
MIN_DELAY = 0.5
MAX_DELAY = 1.2
RETRY_EXTRA = 1
MAX_RETRIES_SEND = 3
# ============================

bot = telebot.TeleBot(BOT_TOKEN)

# ---------- DB (SQLite) helpers ----------
def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY
                    )""")
        conn.commit()
        conn.close()
        save_json_backup()  # create backup file if missing
    except Exception as e:
        print("init_db error:", e)
        traceback.print_exc(file=sys.stdout)

def add_user_db(user_id: int):
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (int(user_id),))
        conn.commit()
        conn.close()
        save_json_backup()
    except Exception as e:
        print("add_user_db error:", e)
        traceback.print_exc(file=sys.stdout)

def remove_user_db(user_id: int):
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE user_id = ?", (int(user_id),))
        conn.commit()
        conn.close()
        save_json_backup()
    except Exception as e:
        print("remove_user_db error:", e)
        traceback.print_exc(file=sys.stdout)

def get_all_users_db():
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT user_id FROM users")
        rows = c.fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        print("get_all_users_db error:", e)
        traceback.print_exc(file=sys.stdout)
        return []

# ---------- JSON backup helpers ----------
def save_json_backup():
    try:
        users = get_all_users_db()
        with open(JSON_BACKUP, "w") as f:
            json.dump(users, f)
    except Exception as e:
        print("save_json_backup error:", e)
        traceback.print_exc(file=sys.stdout)

def load_json_backup_to_db():
    try:
        if not os.path.exists(JSON_BACKUP):
            return
        with open(JSON_BACKUP, "r") as f:
            users = json.load(f)
        for uid in users:
            add_user_db(uid)
    except Exception as e:
        print("load_json_backup_to_db error:", e)
        traceback.print_exc(file=sys.stdout)

# ---------- safe send helpers ----------
def parse_retry_after(text: str):
    m = re.search(r"retry after (\d+)", text, re.IGNORECASE)
    if m:
        try:
            return int(m.group(1))
        except:
            return None
    return None

def safe_send(send_func, *args, **kwargs):
    attempt = 0
    while attempt < MAX_RETRIES_SEND:
        try:
            send_func(*args, **kwargs)
            return True
        except apihelper.ApiTelegramException as e:
            txt = str(e)
            retry = parse_retry_after(txt)
            if retry:
                wait = retry + RETRY_EXTRA
                print(f"[safe_send] FloodWait detected. Sleeping {wait}s (attempt {attempt+1})")
                time.sleep(wait)
                attempt += 1
                continue
            low = txt.lower()
            if "bot was blocked" in low or "forbidden" in low or "user is deactivated" in low:
                print("[safe_send] blocked/forbidden detected:", txt)
                return False
            print("[safe_send] ApiTelegramException:", txt)
            return False
        except Exception as ex:
            print("[safe_send] Exception:", ex)
            traceback.print_exc(file=sys.stdout)
            time.sleep(1 + attempt)
            attempt += 1
    return False

def random_delay():
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

# ---------- Handlers ----------
@bot.message_handler(commands=['start'])
def cmd_start(m):
    try:
        add_user_db(m.from_user.id)
        bot.reply_to(m, "✅ Registered for broadcasts.")
    except Exception as e:
        print("cmd_start error:", e)
        traceback.print_exc(file=sys.stdout)

@bot.chat_join_request_handler()
def join_request_handler(req):
    try:
        # Approve request (bot must be admin with Approve permission)
        bot.approve_chat_join_request(req.chat.id, req.from_user.id)
        add_user_db(req.from_user.id)
        try:
            bot.send_message(req.from_user.id, "✅ Your request approved. Welcome!")
        except Exception:
            pass
        print("Approved & added:", req.from_user.id)
    except Exception as e:
        print("join_request_handler error:", e)
        traceback.print_exc(file=sys.stdout)

@bot.message_handler(commands=['broadcast'])
def cmd_broadcast(m):
    if m.from_user.id != ADMIN_ID:
        return
    users = get_all_users_db()
    if not users:
        bot.reply_to(m, "⚠ No users in DB.")
        return

    reply = m.reply_to_message
    sent = 0
    removed = 0
    failed = 0

    def send_and_handle(uid, func, *fargs, **fkwargs):
        nonlocal sent, removed, failed
        ok = safe_send(func, *fargs, **fkwargs)
        if ok:
            sent += 1
            random_delay()
            return
        # check quickly whether blocked (make a small call)
        try:
            bot.send_chat_action(uid, 'typing')
            failed += 1
            random_delay()
        except apihelper.ApiTelegramException as e2:
            low = str(e2).lower()
            if "bot was blocked" in low or "forbidden" in low or "user is deactivated" in low:
                remove_user_db(uid)
                removed += 1
            else:
                failed += 1
        except Exception:
            failed += 1

    try:
        if reply:
            if reply.photo:
                fid = reply.photo[-1].file_id
                cap = reply.caption or ""
                for uid in users:
                    send_and_handle(uid, bot.send_photo, uid, fid, caption=cap)
            elif reply.video:
                fid = reply.video.file_id
                cap = reply.caption or ""
                for uid in users:
                    send_and_handle(uid, bot.send_video, uid, fid, caption=cap)
            elif reply.document:
                fid = reply.document.file_id
                cap = reply.caption or ""
                for uid in users:
                    send_and_handle(uid, bot.send_document, uid, fid, caption=cap)
            elif reply.audio:
                fid = reply.audio.file_id
                cap = reply.caption or ""
                for uid in users:
                    send_and_handle(uid, bot.send_audio, uid, fid, caption=cap)
            elif reply.voice:
                fid = reply.voice.file_id
                for uid in users:
                    send_and_handle(uid, bot.send_voice, uid, fid)
            elif reply.sticker:
                fid = reply.sticker.file_id
                for uid in users:
                    send_and_handle(uid, bot.send_sticker, uid, fid)
            elif reply.text:
                text = reply.text
                for uid in users:
                    send_and_handle(uid, bot.send_message, uid, text)
            else:
                bot.reply_to(m, "⚠ Unsupported reply type.")
                return
        else:
            text = m.text.replace("/broadcast", "", 1).strip()
            if not text:
                bot.reply_to(m, "⚠ Reply to a message or use /broadcast Your text")
                return
            for uid in users:
                send_and_handle(uid, bot.send_message, uid, text)

        bot.reply_to(m, f"✅ Done. Sent: {sent}  Removed: {removed}  Failed: {failed}")

    except Exception as e:
        print("Broadcast main error:", e)
        traceback.print_exc(file=sys.stdout)
        bot.reply_to(m, f"❌ Broadcast error: {e}")

@bot.message_handler(commands=['count'])
def cmd_count(m):
    if m.from_user.id != ADMIN_ID:
        return
    users = get_all_users_db()
    bot.reply_to(m, f"Total users in DB: {len(users)}")

@bot.message_handler(commands=['export_backup'])
def cmd_export(m):
    if m.from_user.id != ADMIN_ID:
        return
    save_json_backup()
    bot.reply_to(m, f"Backup saved: {JSON_BACKUP}")

# ---------- init ----------
init_db()
load_json_backup_to_db()

# ---------- crash-resilient polling ----------
def run_polling():
    print("Starting polling (crash-resilient)...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception:
            print("Exception in polling, restarting after 10s. Traceback:")
            traceback.print_exc(file=sys.stdout)
            time.sleep(10)
            continue

if _name_ == "__main__":
    t = threading.Thread(target=run_polling, daemon=True)
    t.start()
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Exiting on KeyboardInterrupt")
