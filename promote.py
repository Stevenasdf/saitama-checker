# promote.py - Sistema de Promoción / Degradación (LIMPIO + DB COMPATIBLE)

import logging
import db
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

# ==============================
# CONFIG
# ==============================

DAYS_FOR_ADMIN = 999_999

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
log = logging.getLogger("promote")

# ==============================
# HELPERS
# ==============================

async def get_user_name(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> str:
    try:
        chat = await context.bot.get_chat(user_id)
        return f"@{chat.username}" if chat.username else chat.first_name
    except Exception:
        return str(user_id)

# ==============================
# MENSAJES
# ==============================

def promote_msg(executor, target_id, target_name):
    return (
        "<b>✅ USUARIO PROMOVIDO</b>\n\n"
        f"👤 <b>ID:</b> <code>{target_id}</code>\n"
        f"📝 <b>Nombre:</b> {target_name}\n"
        "🎯 <b>Rango:</b> ADMIN\n"
        f"📅 <b>Días Premium:</b> {DAYS_FOR_ADMIN:,}\n"
        f"👑 <b>Por:</b> {executor}"
    )

def demote_msg(executor, target_id, target_name, old_days):
    return (
        "<b>✅ USUARIO DEGRADADO</b>\n\n"
        f"👤 <b>ID:</b> <code>{target_id}</code>\n"
        f"📝 <b>Nombre:</b> {target_name}\n"
        "🎯 <b>Rango:</b> FREE\n"
        f"📅 <b>Días Anteriores:</b> {old_days:,}\n"
        f"👑 <b>Por:</b> {executor}"
    )

# ==============================
# /PROMOTE
# ==============================

async def handle_promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = update.effective_user.id

    if not db.is_owner(uid):
        return

    if len(context.args) != 1:
        await msg.reply_text(
            "📝 Uso: <code>/promote ID</code>",
            parse_mode="HTML",
            reply_to_message_id=msg.message_id
        )
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await msg.reply_text("❌ ID inválido.", reply_to_message_id=msg.message_id)
        return

    if target_id == uid:
        await msg.reply_text("❌ No puedes promoverte.", reply_to_message_id=msg.message_id)
        return

    user = db.get_user(target_id)
    if not user:
        await msg.reply_text("❌ Usuario no registrado.", reply_to_message_id=msg.message_id)
        return

    if user["rank"] == "admin":
        await msg.reply_text("❌ El usuario ya es admin.", reply_to_message_id=msg.message_id)
        return

    db.update_user_rank(target_id, "admin")
    db.update_user_days(target_id, DAYS_FOR_ADMIN)

    name = await get_user_name(target_id, context)
    executor = update.effective_user.username or update.effective_user.first_name

    await msg.reply_text(
        promote_msg(executor, target_id, name),
        parse_mode="HTML",
        reply_to_message_id=msg.message_id
    )

    log.info(f"{uid} promovió a {target_id}")

# ==============================
# /DEMOTE
# ==============================

async def handle_demote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = update.effective_user.id

    if not db.is_owner(uid):
        return

    if len(context.args) != 1:
        await msg.reply_text(
            "📝 Uso: <code>/demote ID</code>",
            parse_mode="HTML",
            reply_to_message_id=msg.message_id
        )
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await msg.reply_text("❌ ID inválido.", reply_to_message_id=msg.message_id)
        return

    if target_id == uid:
        await msg.reply_text("❌ No puedes degradarte.", reply_to_message_id=msg.message_id)
        return

    user = db.get_user(target_id)
    if not user:
        await msg.reply_text("❌ Usuario no registrado.", reply_to_message_id=msg.message_id)
        return

    if user["rank"] == "free":
        await msg.reply_text("❌ El usuario ya es FREE.", reply_to_message_id=msg.message_id)
        return

    old_days = user["days"]

    db.update_user_rank(target_id, "free")
    if old_days > 0:
        db.update_user_days(target_id, -old_days)

    name = await get_user_name(target_id, context)
    executor = update.effective_user.username or update.effective_user.first_name

    await msg.reply_text(
        demote_msg(executor, target_id, name, old_days),
        parse_mode="HTML",
        reply_to_message_id=msg.message_id
    )

    log.info(f"{uid} degradó a {target_id}")

# ==============================
# /ADMINLIST
# ==============================

async def handle_adminlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = update.effective_user.id

    if not db.is_admin(uid):
        return

    admins = db.q(
        "SELECT user_id FROM users WHERE rank = 'admin'",
        all=True
    )

    text = f"👑 <b>OWNER:</b> <code>{db.OWNER_ID}</code>\n\n"

    if admins:
        text += "🔧 <b>ADMINISTRADORES:</b>\n"
        for a in admins:
            text += f"• <code>{a['user_id']}</code>\n"
    else:
        text += "🔧 No hay administradores.\n"

    text += f"\n━━━━━━━━━━━━━━━━\n<b>Total:</b> {len(admins)}"

    await msg.reply_text(
        text,
        parse_mode="HTML",
        reply_to_message_id=msg.message_id
    )

# ==============================
# COMANDOS CON PUNTO
# ==============================

async def handle_dot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.args = text.split()[1:]

    if text.startswith(".promote"):
        await handle_promote(update, context)
    elif text.startswith(".demote"):
        await handle_demote(update, context)
    elif text == ".adminlist":
        await handle_adminlist(update, context)

# ==============================
# REGISTRO
# ==============================

def register_handlers(application):
    application.add_handler(CommandHandler("promote", handle_promote))
    application.add_handler(CommandHandler("demote", handle_demote))
    application.add_handler(CommandHandler("adminlist", handle_adminlist))

    application.add_handler(
        MessageHandler(
            filters.Regex(r'^\.(promote|demote|adminlist)\b'),
            handle_dot
        )
    )

    log.info("Handlers promote/demote/adminlist registrados")