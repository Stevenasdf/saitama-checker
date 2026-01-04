# addpremium.py - Gestión de Premium (TIME BASED + DB COMPATIBLE)

import logging
import db
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

# ==============================
# CONFIG
# ==============================

MAX_DAYS = 999_999

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
log = logging.getLogger("premium")

# ==============================
# HELPERS
# ==============================

def can_modify(executor_rank: str, target_rank: str) -> bool:
    """
    owner -> cualquiera
    admin -> free / premium
    """
    if executor_rank == "owner":
        return True
    if executor_rank == "admin" and target_rank in ("free", "premium"):
        return True
    return False

# ==============================
# MENSAJES
# ==============================

def add_premium_msg(executor, target_id, added, total):
    return (
        "<b>✅ PREMIUM AGREGADO</b>\n\n"
        f"👤 <b>ID:</b> <code>{target_id}</code>\n"
        f"➕ <b>Días agregados:</b> {added:,}\n"
        f"📅 <b>Días totales:</b> {total:,}\n"
        f"👑 <b>Por:</b> {executor}"
    )


def del_premium_msg(executor, target_id):
    return (
        "<b>✅ PREMIUM ELIMINADO</b>\n\n"
        f"👤 <b>ID:</b> <code>{target_id}</code>\n"
        "🎯 <b>Rango:</b> FREE\n"
        "📅 <b>Días:</b> 0\n"
        f"👑 <b>Por:</b> {executor}"
    )

# ==============================
# /ADDPREMIUM
# ==============================

async def handle_addpremium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = update.effective_user.id

    if not db.is_admin(uid):
        return

    if len(context.args) != 2:
        await msg.reply_text(
            "📝 Uso: <code>/addpremium ID DÍAS</code>",
            parse_mode="HTML",
            reply_to_message_id=msg.message_id
        )
        return

    try:
        target_id = int(context.args[0])
        days = int(context.args[1])
    except ValueError:
        await msg.reply_text(
            "❌ ID y días deben ser números.",
            reply_to_message_id=msg.message_id
        )
        return

    if days <= 0:
        await msg.reply_text(
            "❌ Los días deben ser mayores a 0.",
            reply_to_message_id=msg.message_id
        )
        return

    user = db.get_user(target_id)
    if not user:
        await msg.reply_text(
            "❌ Usuario no registrado.",
            reply_to_message_id=msg.message_id
        )
        return

    executor = db.get_user(uid)
    if not executor:
        return

    if not can_modify(executor["rank"], user["rank"]):
        await msg.reply_text(
            "❌ No tienes permisos para modificar este usuario.",
            reply_to_message_id=msg.message_id
        )
        return

    current_days = db.get_premium_days_left(target_id)
    if current_days >= MAX_DAYS:
        await msg.reply_text(
            f"❌ El usuario ya tiene el máximo de días ({MAX_DAYS:,}).",
            reply_to_message_id=msg.message_id
        )
        return

    allowed_days = min(days, MAX_DAYS - current_days)

    db.add_premium_days(target_id, allowed_days)

    executor_name = (
        update.effective_user.username
        or update.effective_user.first_name
        or str(uid)
    )

    await msg.reply_text(
        add_premium_msg(
            executor_name,
            target_id,
            allowed_days,
            current_days + allowed_days
        ),
        parse_mode="HTML",
        reply_to_message_id=msg.message_id
    )

    log.info(f"{uid} agregó {allowed_days} días premium a {target_id}")

# ==============================
# /DELPREMIUM
# ==============================

async def handle_delpremium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = update.effective_user.id

    if not db.is_admin(uid):
        return

    if len(context.args) != 1:
        await msg.reply_text(
            "📝 Uso: <code>/delpremium ID</code>",
            parse_mode="HTML",
            reply_to_message_id=msg.message_id
        )
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await msg.reply_text(
            "❌ ID inválido.",
            reply_to_message_id=msg.message_id
        )
        return

    user = db.get_user(target_id)
    if not user:
        await msg.reply_text(
            "❌ Usuario no registrado.",
            reply_to_message_id=msg.message_id
        )
        return

    executor = db.get_user(uid)
    if not executor:
        return

    if not can_modify(executor["rank"], user["rank"]):
        await msg.reply_text(
            "❌ No tienes permisos para modificar este usuario.",
            reply_to_message_id=msg.message_id
        )
        return

    db.remove_premium(target_id)

    executor_name = (
        update.effective_user.username
        or update.effective_user.first_name
        or str(uid)
    )

    await msg.reply_text(
        del_premium_msg(executor_name, target_id),
        parse_mode="HTML",
        reply_to_message_id=msg.message_id
    )

    log.info(f"{uid} eliminó premium de {target_id}")

# ==============================
# COMANDOS CON PUNTO
# ==============================

async def handle_dot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.args = text.split()[1:]

    if text.startswith(".addpremium"):
        await handle_addpremium(update, context)
    elif text.startswith(".delpremium"):
        await handle_delpremium(update, context)

# ==============================
# REGISTRO
# ==============================

def register_handlers(application):
    application.add_handler(CommandHandler("addpremium", handle_addpremium))
    application.add_handler(CommandHandler("delpremium", handle_delpremium))

    application.add_handler(
        MessageHandler(
            filters.Regex(r'^\.(addpremium|delpremium)\b'),
            handle_dot
        )
    )

    log.info("Handlers premium registrados")