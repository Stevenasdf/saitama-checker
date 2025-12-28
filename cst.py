# cst.py - Stripe Site Checker (FINAL DB COMPATIBLE)

import asyncio
import aiohttp
import db
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

STRIPE_API_BASE = "https://md-auto-stripe.onrender.com/gateway=AutoStripe/key=md-tech"
TEST_CC = "4487757834478421|04|2030|887"

TIMEOUT = aiohttp.ClientTimeout(total=45)

# ==============================
# RESPUESTAS VÁLIDAS
# ==============================

VALID_RESPONSES = {
    "card added",
    "your card's security code is incorrect",
    "your card number is incorrect",
    "your card was declined",
    "this credit card type is not accepted",
    "your card does not support this type of purchase",
}

# ==============================
# HELPERS
# ==============================

def clean_site(site: str) -> str:
    return (
        site.replace("https://", "")
        .replace("http://", "")
        .replace("www.", "")
        .strip()
    )


def is_valid_response(resp: str) -> bool:
    if not resp:
        return False
    r = resp.lower()
    return any(v in r for v in VALID_RESPONSES)


async def check_site(session: aiohttp.ClientSession, site: str):
    site_clean = clean_site(site)
    url = f"{STRIPE_API_BASE}/site={site_clean}/cc={TEST_CC}"

    try:
        async with session.get(url) as r:
            data = await r.json()
            return site, data.get("Response", "N/A")
    except Exception as e:
        return site, str(e)[:40]

# ==============================
# /CST
# ==============================

async def handle_cst(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = update.effective_user.id

    if not db.get_user(uid):
        await msg.reply_text(
            "❌ Debes registrarte primero usando <code>/register</code>.",
            parse_mode="HTML",
            reply_to_message_id=msg.message_id,
        )
        return

    sites = db.get_user_stripe_sites(uid)

    if not sites:
        await msg.reply_text(
            "📭 No tienes sitios Stripe.",
            reply_to_message_id=msg.message_id,
        )
        return

    status = await msg.reply_text(
        f"🔍 <b>Checking {len(sites)} Stripe sites...</b>",
        parse_mode="HTML",
        reply_to_message_id=msg.message_id,
    )

    removed = 0
    results = []

    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        for site in sites:
            site_name, response = await check_site(session, site)

            results.append(
                f"Site: {site_name}\n"
                f"Response: {response}\n"
            )

            if not is_valid_response(response):
                db.remove_user_stripe_site(uid, site_name)
                removed += 1

            await asyncio.sleep(0.35)

    final = (
        "<b>💳 STRIPE SITE CHECK</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"<pre>{chr(10).join(results)}</pre>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Total:</b> {len(sites)}\n"
        f"🗑️ <b>Removed:</b> {removed}"
    )

    await status.edit_text(
        final,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

# ==============================
# COMANDOS CON PUNTO
# ==============================

async def handle_dot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == ".cst":
        await handle_cst(update, context)

# ==============================
# REGISTRO
# ==============================

def register_handlers(application):
    application.add_handler(CommandHandler("cst", handle_cst))
    application.add_handler(
        MessageHandler(filters.Regex(r"^\.cst$"), handle_dot)
    )