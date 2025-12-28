# cmds.py - Menú de comandos (LIMPIO + DB COMPATIBLE)

import db
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

START_GIF = "https://media.giphy.com/media/oxbNORcXx76F2/giphy.gif"

# ==============================
# UTILIDAD ENVÍO / EDICIÓN
# ==============================

async def send_or_edit(update: Update, text: str, keyboard: list):
    markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        q = update.callback_query
        try:
            await q.edit_message_caption(
                caption=text,
                parse_mode="HTML",
                reply_markup=markup,
            )
            return
        except Exception:
            pass

        try:
            await q.edit_message_text(
                text=text,
                parse_mode="HTML",
                reply_markup=markup,
            )
            return
        except Exception:
            pass

        await q.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=markup,
        )
        return

    # mensaje normal
    try:
        await update.message.reply_animation(
            animation=START_GIF,
            caption=text,
            parse_mode="HTML",
            reply_markup=markup,
            reply_to_message_id=update.message.message_id,
        )
    except Exception:
        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=markup,
            reply_to_message_id=update.message.message_id,
        )

# ==============================
# MENÚ PRINCIPAL
# ==============================

async def show_cmds_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = (
        update.callback_query.from_user
        if update.callback_query
        else update.effective_user
    )

    text = (
        f"<b>👋 Bienvenido {user.first_name}!</b>\n\n"
        "<b>Selecciona una categoría:</b>"
    )

    keyboard = [
        [
            InlineKeyboardButton("Gateways", callback_data="gateways"),
            InlineKeyboardButton("Tools", callback_data="tools"),
        ],
        [InlineKeyboardButton("Close", callback_data="close")],
    ]

    await send_or_edit(update, text, keyboard)

# ==============================
# /CMDS
# ==============================

async def handle_cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = update.effective_user.id

    if not db.get_user(uid):
        await msg.reply_text(
            "❌ Debes registrarte primero usando <code>/register</code>.",
            parse_mode="HTML",
            reply_to_message_id=msg.message_id,
        )
        return

    await show_cmds_menu(update, context)

# ==============================
# GATEWAYS
# ==============================

async def show_gateways(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_or_edit(
        update,
        "<b>🔌 Gateways</b>",
        [
            [
                InlineKeyboardButton("Proxy", callback_data="gateway_proxy"),
                InlineKeyboardButton("Shopify", callback_data="gateway_shopify"),
                InlineKeyboardButton("Stripe", callback_data="gateway_stripe"),
            ],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_main")],
        ],
    )

async def show_proxy_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_or_edit(
        update,
        (
            "<b>Proxy Management</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            "<code>/add</code> - Add proxies\n"
            "<code>/remove</code> - Remove proxies\n"
            "<code>/show</code> - Show all proxies\n"
            "<code>/delete</code> - Delete all proxies\n"
            "<code>/check</code> - Check all proxies\n"
            "━━━━━━━━━━━━━━━━\n"
            "Format: <code>ip:port:user:pass</code>"
        ),
        [[InlineKeyboardButton("⬅️ Back", callback_data="gateways")]],
    )

async def show_shopify_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_or_edit(
        update,
        (
            "<b>Shopify Management</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            "<code>/ash</code> - Add sites\n"
            "<code>/rsh</code> - Remove sites\n"
            "<code>/ssh</code> - Show all sites\n"
            "<code>/dsh</code> - Delete all sites\n"
            "<code>/csh</code> - Check all sites\n"
            "━━━━━━━━━━━━━━━━\n"
            "<code>/sh n|mm|yy|cvv</code> - Single Check\n"
            "<code>/msh n|mm|yy|cvv</code> - Mass Check (20)\n"
            "━━━━━━━━━━━━━━━━"
        ),
        [[InlineKeyboardButton("⬅️ Back", callback_data="gateways")]],
    )

async def show_stripe_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_or_edit(
        update,
        (
            "<b>Stripe Management</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            "<code>/ast</code> - Add sites\n"
            "<code>/rst</code> - Remove sites\n"
            "<code>/sst</code> - Show all sites\n"
            "<code>/dst</code> - Delete all sites\n"
            "<code>/cst</code> - Check all sites\n"
            "━━━━━━━━━━━━━━━━\n"
            "<code>/st n|mm|yy|cvv</code> - Single Check\n"
            "<code>/mst n|mm|yy|cvv</code> - Mass Check (20)\n"
            "━━━━━━━━━━━━━━━━"
        ),
        [[InlineKeyboardButton("⬅️ Back", callback_data="gateways")]],
    )

# ==============================
# TOOLS
# ==============================

async def show_tools(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_or_edit(
        update,
        (
            "<b>🛠️ Tools</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            "<code>/info</code> - User info\n"
            "<code>/bin 123456</code> - BIN lookup\n"
            "<code>/gen 123456</code> - CC generator\n"
            "━━━━━━━━━━━━━━━━"
        ),
        [[InlineKeyboardButton("⬅️ Back", callback_data="back_main")]],
    )

# ==============================
# BOTONES
# ==============================

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id

    if not db.get_user(uid):
        await q.answer("❌ Debes registrarte primero.", show_alert=True)
        return

    handlers = {
        "gateways": show_gateways,
        "tools": show_tools,
        "gateway_proxy": show_proxy_info,
        "gateway_shopify": show_shopify_info,
        "gateway_stripe": show_stripe_info,
        "back_main": show_cmds_menu,
        "close": close_menu,
    }

    await q.answer()

    handler = handlers.get(q.data)
    if handler:
        await handler(update, context)

async def close_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("Menu closed")
    await q.delete_message()

# ==============================
# COMANDO CON PUNTO
# ==============================

async def handle_dot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == ".cmds":
        await handle_cmds(update, context)

# ==============================
# REGISTRO
# ==============================

def register_handlers(application):
    application.add_handler(CommandHandler("cmds", handle_cmds))
    application.add_handler(
        MessageHandler(filters.Regex(r"^\.cmds$"), handle_dot)
    )
    application.add_handler(
        CallbackQueryHandler(
            handle_button,
            pattern="^(gateways|tools|gateway_proxy|gateway_shopify|gateway_stripe|back_main|close)$",
        )
    )