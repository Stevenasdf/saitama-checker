# start.py - Start & Register (FINAL DEFINITIVO)

import db
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

# ==============================
# /START
# ==============================

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message

    # Usuario NO registrado
    if not db.get_user(user.id):
        await msg.reply_text(
            (
                f"<b>👋 ¡Hola {user.first_name}!</b>\n\n"
                "Bienvenido a <b>SaitamaChk</b> 🥊\n\n"
                "📝 Regístrate usando:\n"
                "<code>/register</code> o <code>.register</code>"
            ),
            parse_mode="HTML",
            reply_to_message_id=msg.message_id,
        )
        return

    # Usuario registrado → enviar directamente a /cmds
    from cmds import handle_cmds
    await handle_cmds(update, context)

# ==============================
# /REGISTER
# ==============================

async def handle_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message

    # Ya registrado
    if db.get_user(user.id):
        await msg.reply_text(
            "ℹ️ Ya estás registrado.\n💡 Usa <code>/cmds</code> para ver el menú.",
            parse_mode="HTML",
            reply_to_message_id=msg.message_id,
        )
        return

    ok, error = db.register_user(user.id)
    if not ok:
        await msg.reply_text("❌ Error al registrarte.")
        return

    data = db.get_user(user.id)

    await msg.reply_text(
        (
            "<b>✅ REGISTRO COMPLETADO</b>\n\n"
            f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
            f"🏷 <b>Rango:</b> {data['rank'].upper()}\n"
            f"⏳ <b>Días:</b> {data['days']:,}\n\n"
            "💡 Usa <code>/cmds</code> para continuar."
        ),
        parse_mode="HTML",
        reply_to_message_id=msg.message_id,
    )

# ==============================
# COMANDOS CON PUNTO
# ==============================

async def handle_dot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == ".start":
        await handle_start(update, context)
    elif text == ".register":
        await handle_register(update, context)

# ==============================
# REGISTRO DE HANDLERS
# ==============================

def register_handlers(application):
    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(CommandHandler("register", handle_register))

    application.add_handler(
        MessageHandler(filters.Regex(r"^\.(start|register)$"), handle_dot)
    )