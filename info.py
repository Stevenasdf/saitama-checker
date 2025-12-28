# info.py - User Info (LOOKUP TELEGRAM + DB)
# PTB v20+ | DB SAFE

import time
import html
import traceback
import db

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

BOT_TAG = '<a href="http://t.me/SaitamaChecker_Bot">[拳]</a>'

# ==============================
# UTILIDAD
# ==============================

def format_date(ts: int) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))

def esc(v):
    return html.escape(str(v))

def safe_int(v, default):
    try:
        return int(v)
    except Exception:
        return default

# ==============================
# /info y .info
# ==============================

async def handle_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = update.message
        text = msg.text.strip()

        requester = update.effective_user
        requester_name = requester.username or requester.first_name or "Unknown"

        # ======================
        # PARSE ARGUMENTOS
        # ======================
        parts = text.split(maxsplit=1)
        args = parts[1].split() if len(parts) > 1 else []

        if args:
            arg = args[0]
            if arg.startswith("@"):
                target = arg
            else:
                try:
                    target = int(arg)
                except ValueError:
                    await msg.reply_text("❌ ID o @username inválido.")
                    return
        else:
            target = requester.id

        # ======================
        # TELEGRAM LOOKUP
        # ======================
        try:
            chat = await context.bot.get_chat(target)
        except Exception:
            await msg.reply_text("❌ Usuario no encontrado.")
            return

        name = esc(chat.first_name or "Unknown")
        username = f"@{esc(chat.username)}" if chat.username else "None"
        user_id = chat.id

        # ======================
        # DB LOOKUP
        # ======================
        user = db.get_user(user_id)
        if not isinstance(user, dict):
            user = None

        # ======================
        # RESPUESTA
        # ======================
        if not user:
            text = (
                f"{BOT_TAG} <b>User Info</b>\n"
                "━━━━━━━━━━━━━━━━\n"
                f"{BOT_TAG} <b>Name:</b> {name}\n"
                f"{BOT_TAG} <b>User:</b> {username}\n"
                f"{BOT_TAG} <b>ID:</b> <code>{user_id}</code>\n"
                "━━━━━━━━━━━━━━━━\n"
                f"{BOT_TAG} <b>Req by:</b> @{esc(requester_name)}"
            )
        else:
            rank = esc(str(user.get("rank", "free")).upper())
            days = safe_int(user.get("days"), 0)

            raw_ts = user.get("registered_at")
            created_at = safe_int(raw_ts, int(time.time()))

            text = (
                f"{BOT_TAG} <b>User Info</b>\n"
                "━━━━━━━━━━━━━━━━\n"
                f"{BOT_TAG} <b>Name:</b> {name}\n"
                f"{BOT_TAG} <b>User:</b> {username}\n"
                f"{BOT_TAG} <b>ID:</b> <code>{user_id}</code>\n"
                f"{BOT_TAG} <b>Rank:</b> {rank}\n"
                f"{BOT_TAG} <b>Days:</b> {days:,}\n"
                f"{BOT_TAG} <b>Registered at:</b> {format_date(created_at)}\n"
                "━━━━━━━━━━━━━━━━\n"
                f"{BOT_TAG} <b>Req by:</b> @{esc(requester_name)}"
            )

        await msg.reply_text(
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_to_message_id=msg.message_id
        )

    except Exception:
        print("INFO ERROR:\n", traceback.format_exc())
        await update.message.reply_text(
            "❌ Error interno al procesar /info."
        )

# ==============================
# REGISTRO
# ==============================

def register_handlers(application):
    application.add_handler(
        MessageHandler(
            filters.Regex(r"^(\/info|\.info)\b"),
            handle_info
        )
    )