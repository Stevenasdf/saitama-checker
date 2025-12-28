# bin.py - BIN Lookup (FINAL DEFINITIVO · SaitamaChk)

import re
import requests
import db
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

API_URL = "https://bins.antipublic.cc/bins/"
TIMEOUT = 10

BOT_TAG = '<a href="http://t.me/SaitamaChecker_Bot">[拳]</a>'

# ==============================
# UTILIDADES
# ==============================

def extract_bin(text: str) -> str:
    clean = re.sub(r"[^\d]", "", text)
    return clean[:6] if len(clean) >= 6 else ""


def fetch_bin(bin_number: str) -> dict:
    try:
        r = requests.get(f"{API_URL}{bin_number}", timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


# ==============================
# FUNCIÓN PÚBLICA (USADA POR OTROS MÓDULOS)
# ==============================

def get_bin_info(bin_number: str) -> dict:
    data = fetch_bin(bin_number)

    if not data:
        return {
            "success": False,
            "info": "N/A",
            "bank": "N/A",
            "country": "N/A",
        }

    info = " - ".join(
        x for x in [
            data.get("brand"),
            data.get("type"),
            data.get("level"),
        ] if x
    )

    country = data.get("country_name", "N/A")
    flag = data.get("country_flag", "")

    return {
        "success": True,
        "info": info.upper() if info else "N/A",
        "bank": data.get("bank", "N/A"),
        "country": f"{country} {flag}".strip(),
    }

# ==============================
# FORMATO
# ==============================

def format_bin(bin_number: str, data: dict, user: str) -> str:
    return (
        f"{BOT_TAG} <b>BIN Lookup</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"{BOT_TAG} <b>BIN:</b> <code>{bin_number}</code>\n"
        f"{BOT_TAG} <b>Info:</b> <code>{data['info']}</code>\n"
        f"{BOT_TAG} <b>Bank:</b> <code>{data['bank']}</code>\n"
        f"{BOT_TAG} <b>Country:</b> <code>{data['country']}</code>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"{BOT_TAG} <b>Req by:</b> @{user}"
    )

# ==============================
# /BIN
# ==============================

async def handle_bin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = update.effective_user
    username = user.username or user.first_name

    if not db.get_user(user.id):
        await msg.reply_text(
            "❌ Debes registrarte primero usando <code>/register</code>.",
            parse_mode="HTML",
            reply_to_message_id=msg.message_id
        )
        return

    if not context.args:
        await msg.reply_text(
            "⚠️ Uso: <code>/bin 123456</code>",
            parse_mode="HTML",
            reply_to_message_id=msg.message_id
        )
        return

    bin_number = extract_bin(" ".join(context.args))
    if len(bin_number) != 6:
        await msg.reply_text(
            "❌ BIN inválido (6 dígitos requeridos).",
            reply_to_message_id=msg.message_id
        )
        return

    loading = await msg.reply_text(
        f"🔍 Buscando BIN <code>{bin_number}</code>...",
        parse_mode="HTML",
        reply_to_message_id=msg.message_id
    )

    data = get_bin_info(bin_number)
    if not data["success"]:
        await loading.edit_text("❌ BIN no encontrado.")
        return

    await loading.edit_text(
        format_bin(bin_number, data, username),
        parse_mode="HTML",
        disable_web_page_preview=True
    )

# ==============================
# COMANDOS CON PUNTO
# ==============================

async def handle_dot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith(".bin"):
        context.args = text.split()[1:]
        await handle_bin(update, context)

# ==============================
# REGISTRO
# ==============================

def register_handlers(application):
    application.add_handler(CommandHandler("bin", handle_bin))
    application.add_handler(
        MessageHandler(filters.Regex(r"^\.bin\b"), handle_dot)
    )