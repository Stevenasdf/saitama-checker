# panel.py - Panel de Administración (LIMPIO + DB COMPATIBLE)

import db
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# ==============================
# HELPERS
# ==============================

def get_uid(update: Update) -> int | None:
    if update.callback_query:
        return update.callback_query.from_user.id
    if update.message:
        return update.effective_user.id
    return None


async def deny_access(update: Update):
    if update.callback_query:
        await update.callback_query.answer("❌ Acceso denegado", show_alert=True)
    elif update.message:
        await update.message.reply_text(
            "❌ Acceso denegado",
            reply_to_message_id=update.message.message_id
        )

# ==============================
# MENÚ PRINCIPAL
# ==============================

async def show_panel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = get_uid(update)
    if not uid or not db.is_admin(uid):
        await deny_access(update)
        return

    text = "<b>🛡 PANEL DE ADMINISTRACIÓN</b>"

    keyboard = [
        [
            InlineKeyboardButton("👥 Users", callback_data="panel_users"),
            InlineKeyboardButton("📢 Broadcast", callback_data="panel_broadcast"),
        ],
        [InlineKeyboardButton("❌ Close", callback_data="close_panel")],
    ]

    markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        q = update.callback_query
        await q.edit_message_text(
            text=text,
            parse_mode="HTML",
            reply_markup=markup
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=markup,
            reply_to_message_id=update.message.message_id
        )

# ==============================
# /PANEL
# ==============================

async def handle_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_panel_menu(update, context)

# ==============================
# USERS SECTION
# ==============================

async def show_users_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = get_uid(update)
    if not uid or not db.is_admin(uid):
        await deny_access(update)
        return

    text = (
        "<b>👥 USERS MANAGEMENT</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        "<code>/stats</code> - Estadísticas\n"
        "<code>/promote ID</code> - Promover a admin (owner)\n"
        "<code>/demote ID</code> - Degradar a free (owner)\n"
        "<code>/adminlist</code> - Lista admins\n"
        "<code>/addpremium ID DÍAS</code> - Agregar premium\n"
        "<code>/delpremium ID</code> - Quitar premium\n"
        "━━━━━━━━━━━━━━━━"
    )

    await update.callback_query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Back", callback_data="back_panel")]]
        ),
    )

# ==============================
# BROADCAST SECTION
# ==============================

async def show_broadcast_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = get_uid(update)
    if not uid or not db.is_admin(uid):
        await deny_access(update)
        return

    text = (
        "<b>📢 BROADCAST MANAGEMENT</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        "<code>/broadcast MENSAJE</code> - Enviar a todos\n"
        "<code>/bstats</code> - Stats broadcast\n"
        "<code>/cancel</code> - Cancelar broadcast\n"
        "━━━━━━━━━━━━━━━━"
    )

    await update.callback_query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Back", callback_data="back_panel")]]
        ),
    )

# ==============================
# BOTONES
# ==============================

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id

    if not db.is_admin(uid):
        await q.answer("❌ Acceso denegado", show_alert=True)
        return

    handlers = {
        "panel_users": show_users_section,
        "panel_broadcast": show_broadcast_section,
        "back_panel": show_panel_menu,
        "close_panel": close_panel,
    }

    await q.answer()

    handler = handlers.get(q.data)
    if handler:
        await handler(update, context)

async def close_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("Panel cerrado")
    await q.delete_message()

# ==============================
# COMANDO CON PUNTO
# ==============================

async def handle_dot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == ".panel":
        await handle_panel(update, context)

# ==============================
# REGISTRO
# ==============================

def register_handlers(application):
    application.add_handler(CommandHandler("panel", handle_panel))
    application.add_handler(
        MessageHandler(filters.Regex(r"^\.panel$"), handle_dot)
    )
    application.add_handler(
        CallbackQueryHandler(
            handle_button,
            pattern="^(panel_users|panel_broadcast|back_panel|close_panel)$"
        )
    )