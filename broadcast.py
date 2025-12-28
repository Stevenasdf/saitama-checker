# broadcast.py - Sistema de Broadcast (LIMPIO + DB COMPATIBLE)

import logging
import asyncio
import db
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

# ==============================
# CONFIG
# ==============================

BROADCAST_DELAY = 0.1
UPDATE_INTERVAL = 10

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
log = logging.getLogger("broadcast")

# ==============================
# FORMATEO
# ==============================

def bstats_msg(total: int) -> str:
    est = total * BROADCAST_DELAY
    return (
        "<b>📊 BROADCAST STATS</b>\n\n"
        f"👥 <b>Usuarios:</b> {total:,}\n"
        f"⏱️ <b>Tiempo estimado:</b> {est:.0f}s\n\n"
        "<b>Configuración</b>\n"
        f"• Delay: {BROADCAST_DELAY}s\n"
        f"• Update: cada {UPDATE_INTERVAL}"
    )

# ==============================
# /BROADCAST
# ==============================

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = update.effective_user.id

    # Permisos
    if not (db.is_owner(uid) or db.is_admin(uid)):
        return

    if not context.args:
        await msg.reply_text(
            "📝 Uso: <code>/broadcast MENSAJE</code>",
            parse_mode="HTML",
            reply_to_message_id=msg.message_id
        )
        return

    users = db.q(
        "SELECT user_id FROM users",
        all=True
    )

    total = len(users)
    if total == 0:
        await msg.reply_text(
            "❌ No hay usuarios registrados.",
            reply_to_message_id=msg.message_id
        )
        return

    text = " ".join(context.args)

    progress_msg = await msg.reply_text(
        f"📤 <b>Iniciando broadcast</b>\n👥 {total} usuarios",
        parse_mode="HTML",
        reply_to_message_id=msg.message_id
    )

    context.user_data["broadcast"] = True
    sent = failed = 0

    for i, user in enumerate(users, 1):
        if not context.user_data.get("broadcast"):
            break

        try:
            await context.bot.send_message(
                chat_id=user["user_id"],
                text=text,
                parse_mode="HTML"
            )
            sent += 1
        except Exception:
            failed += 1

        if i % UPDATE_INTERVAL == 0 or i == total:
            percent = (i / total) * 100
            await progress_msg.edit_text(
                f"📤 <b>Enviando...</b>\n"
                f"👥 {i}/{total} ({percent:.0f}%)\n"
                f"✅ {sent} enviados\n"
                f"❌ {failed} fallidos",
                parse_mode="HTML"
            )

        await asyncio.sleep(BROADCAST_DELAY)

    cancelled = not context.user_data.get("broadcast", True)

    result = (
        "🛑 <b>Broadcast cancelado</b>\n"
        if cancelled else
        "✅ <b>Broadcast completado</b>\n"
    )

    result += f"\n✅ Enviados: {sent}\n❌ Fallidos: {failed}"

    await progress_msg.edit_text(result, parse_mode="HTML")

    context.user_data.clear()
    log.info(f"{uid} terminó broadcast: {sent} OK / {failed} FAIL")

# ==============================
# /BSTATS
# ==============================

async def handle_bstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = update.effective_user.id

    if not (db.is_owner(uid) or db.is_admin(uid)):
        return

    total = db.q(
        "SELECT COUNT(*) c FROM users",
        one=True
    )["c"]

    await msg.reply_text(
        bstats_msg(total),
        parse_mode="HTML",
        reply_to_message_id=msg.message_id
    )

# ==============================
# /CANCEL
# ==============================

async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = update.effective_user.id

    if not (db.is_owner(uid) or db.is_admin(uid)):
        return

    if not context.user_data.get("broadcast"):
        await msg.reply_text(
            "ℹ️ No hay broadcast activo.",
            reply_to_message_id=msg.message_id
        )
        return

    context.user_data["broadcast"] = False

    await msg.reply_text(
        "🛑 Cancelando broadcast...",
        reply_to_message_id=msg.message_id
    )

# ==============================
# COMANDOS CON PUNTO
# ==============================

async def handle_dot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.args = text.split()[1:]

    if text.startswith(".broadcast"):
        await handle_broadcast(update, context)
    elif text == ".bstats":
        await handle_bstats(update, context)
    elif text == ".cancel":
        await handle_cancel(update, context)

# ==============================
# REGISTRO
# ==============================

def register_handlers(application):
    application.add_handler(CommandHandler("broadcast", handle_broadcast))
    application.add_handler(CommandHandler("bstats", handle_bstats))
    application.add_handler(CommandHandler("cancel", handle_cancel))

    application.add_handler(
        MessageHandler(
            filters.Regex(r'^\.(broadcast|bstats|cancel)\b'),
            handle_dot
        )
    )

    log.info("Handlers broadcast registrados")