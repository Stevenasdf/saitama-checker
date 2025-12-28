# check.py - Proxy Cleaner (FINAL · TCP + HTTPBIN)

import asyncio
import socket
import time
import requests
import db
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

BOT_TAG = "<b>[拳]</b>"

# ==============================
# CONFIG
# ==============================

TCP_TIMEOUT = 6
HTTP_TIMEOUT = 8
MAX_CONCURRENT = 30
HTTPBIN_URL = "http://httpbin.org/ip"

# ==============================
# TCP CHECK
# ==============================

async def tcp_check(proxy: str) -> bool:
    try:
        host, port, *_ = proxy.split(":")
        port = int(port)

        loop = asyncio.get_running_loop()
        fut = loop.run_in_executor(
            None,
            lambda: socket.create_connection((host, port), timeout=TCP_TIMEOUT)
        )

        sock = await asyncio.wait_for(fut, timeout=TCP_TIMEOUT)
        sock.close()
        return True

    except Exception:
        return False

# ==============================
# HTTPBIN CHECK (REAL USO)
# ==============================

def httpbin_check_sync(proxy: str) -> bool:
    try:
        host, port, user, pwd = proxy.split(":")
        proxy_url = f"http://{user}:{pwd}@{host}:{port}"

        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }

        r = requests.get(
            HTTPBIN_URL,
            proxies=proxies,
            timeout=HTTP_TIMEOUT,
            verify=False
        )

        return r.status_code == 200

    except Exception:
        return False

async def httpbin_check(proxy: str) -> bool:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, httpbin_check_sync, proxy)

# ==============================
# CHECK PROXY (COMBINADO)
# ==============================

async def check_proxy(proxy: str) -> bool:
    # 1️⃣ TCP
    if not await tcp_check(proxy):
        return False

    # 2️⃣ HTTPBIN
    if not await httpbin_check(proxy):
        return False

    return True

# ==============================
# /CHECK
# ==============================

async def handle_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    if not db.get_user(uid):
        await msg.reply_text(
            "❌ Debes registrarte primero usando <code>/register</code>.",
            parse_mode="HTML",
            reply_to_message_id=msg.message_id
        )
        return

    proxies = db.get_user_proxies(uid)
    if not proxies:
        await msg.reply_text(
            "📭 No tienes proxies guardadas.",
            reply_to_message_id=msg.message_id
        )
        return

    start = time.time()

    status = await msg.reply_text(
        f"🔍 <b>Checking Proxies (TCP + HTTP)...</b>\n"
        f"📊 <b>Total:</b> {len(proxies)}",
        parse_mode="HTML",
        reply_to_message_id=msg.message_id
    )

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def worker(proxy):
        async with semaphore:
            ok = await check_proxy(proxy)
            return proxy, ok

    tasks = [worker(p) for p in proxies]
    results = await asyncio.gather(*tasks)

    alive = 0
    removed = 0

    for proxy, ok in results:
        if ok:
            alive += 1
        else:
            db.remove_user_proxy(uid, proxy)
            removed += 1

    elapsed = time.time() - start

    final = (
        f"{BOT_TAG} <b>Proxy Check</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"{BOT_TAG} <b>Alive:</b> {alive}\n"
        f"{BOT_TAG} <b>Removed:</b> {removed}\n"
        f"{BOT_TAG} <b>Total:</b> {len(proxies)}\n"
        "━━━━━━━━━━━━━━━━\n"
        f"{BOT_TAG} <b>Time:</b> {elapsed:.2f}s\n"
        f"{BOT_TAG} <b>Req by:</b> @{username}"
    )

    await status.edit_text(
        final,
        parse_mode="HTML",
        disable_web_page_preview=True
    )

# ==============================
# DOT
# ==============================

async def handle_dot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == ".check":
        await handle_check(update, context)

# ==============================
# REGISTER
# ==============================

def register_handlers(application):
    application.add_handler(CommandHandler("check", handle_check))
    application.add_handler(
        MessageHandler(filters.Regex(r"^\.check$"), handle_dot)
    )