# csh.py - Shopify Site Checker (FINAL DB COMPATIBLE)

import asyncio
import aiohttp
import db
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

# ==============================
# CONFIG - NUEVA API
# ==============================

API_URL = "https://shopi-production-7ef9.up.railway.app/"
TEST_CARD = "4737023061083279|08|2028|833"

# ==============================
# RESPUESTAS VÁLIDAS
# ==============================

VALID_RESPONSES = {
    "3d_authentication",
    "insufficient_funds",
    "incorrect_zip",
    "order_completed",
    "order completed",
    "order_placed",
    "order placed",
    "thank_you",
    "thank you",
    "incorrect_cvc",
    "invalid_cvc",
    "card_declined",
    "generic_error",
    "incorrect_number",
    "processing_error",
    "fraud_suspected",
    "risky",
}

# ==============================
# HELPERS
# ==============================

def format_site(site: str) -> str:
    site = site.strip()
    return site if site.startswith(("http://", "https://")) else f"https://{site}"


def is_valid_response(resp: str) -> bool:
    if not resp:
        return False
    r = resp.lower()
    return any(v in r for v in VALID_RESPONSES)


async def check_site(session: aiohttp.ClientSession, site: str, proxy: str):
    params = {
        "url": format_site(site),   # ← cambiado
        "cc": TEST_CARD,
        "proxy": proxy,
    }

    timeout = aiohttp.ClientTimeout(total=60, connect=15)

    try:
        async with session.get(API_URL, params=params, timeout=timeout) as r:
            data = await r.json()
            return (
                data.get("Gate", "N/A"),     # ← cambiado
                data.get("Price", "0"),
                data.get("Response", "N/A"),
            )
    except Exception as e:
        return ("Error", "0", str(e)[:40])

# ==============================
# /CSH
# ==============================

async def handle_csh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = update.effective_user.id

    if not db.get_user(uid):
        await msg.reply_text(
            "❌ Debes registrarte primero usando <code>/register</code>.",
            parse_mode="HTML",
            reply_to_message_id=msg.message_id,
        )
        return

    sites = db.get_user_shopify_sites(uid)
    proxies = db.get_user_proxies(uid)

    if not sites:
        await msg.reply_text(
            "📭 No tienes sitios Shopify.",
            reply_to_message_id=msg.message_id,
        )
        return

    if not proxies:
        await msg.reply_text(
            "❌ No tienes proxies configuradas.",
            reply_to_message_id=msg.message_id,
        )
        return

    status = await msg.reply_text(
        f"🔍 <b>Checking {len(sites)} Shopify sites...</b>",
        parse_mode="HTML",
        reply_to_message_id=msg.message_id,
    )

    removed = 0
    results = []
    proxy_idx = 0

    async with aiohttp.ClientSession() as session:
        for site in sites:
            proxy = proxies[proxy_idx % len(proxies)]
            proxy_num = (proxy_idx % len(proxies)) + 1
            proxy_idx += 1

            gateway, price, response = await check_site(session, site, proxy)

            results.append(
                f"Site: {site}\n"
                f"Gateway: {gateway} {price}\n"
                f"Response: {response}\n"
                f"Proxy: {proxy_num}\n"
            )

            if not is_valid_response(response):
                db.remove_user_shopify_site(uid, site)
                removed += 1

            await asyncio.sleep(0.35)

    final = (
        "<b>🛒 SHOPIFY SITE CHECK</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"<pre>{chr(10).join(results)}</pre>"
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
    if update.message.text.strip() == ".csh":
        await handle_csh(update, context)

# ==============================
# REGISTRO
# ==============================

def register_handlers(application):
    application.add_handler(CommandHandler("csh", handle_csh))
    application.add_handler(
        MessageHandler(filters.Regex(r"^\.csh$"), handle_dot)
    )