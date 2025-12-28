# stats.py - Sistema de Estadísticas (LIMPIO + DB COMPATIBLE)

import db
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

# ==============================
# FORMATEO
# ==============================

def format_stats(stats: dict) -> str:
    return (
        "<b>📊 ESTADÍSTICAS DEL SISTEMA</b>\n\n"
        "<u>👥 USUARIOS</u>\n"
        f"• Total registrados: <b>{stats['total_users']:,}</b>\n"
        f"• Administradores: <b>{stats['admin_users']:,}</b>\n"
        f"• Premium: <b>{stats['premium_users']:,}</b>\n"
        f"• Free: <b>{stats['free_users']:,}</b>\n\n"
        "<u>📦 RECURSOS</u>\n"
        f"• Proxies: <b>{stats['total_proxies']:,}</b>\n"
        f"• Sitios Shopify: <b>{stats['total_shopify_sites']:,}</b>\n"
        f"• Sitios Stripe: <b>{stats['total_stripe_sites']:,}</b>"
    )

# ==============================
# DB
# ==============================

def get_system_stats() -> dict:
    return {
        "total_users": db.q(
            "SELECT COUNT(*) c FROM users",
            one=True
        )["c"],
        "admin_users": db.q(
            "SELECT COUNT(*) c FROM users WHERE rank = 'admin'",
            one=True
        )["c"],
        "premium_users": db.q(
            "SELECT COUNT(*) c FROM users WHERE rank = 'premium'",
            one=True
        )["c"],
        "free_users": db.q(
            "SELECT COUNT(*) c FROM users WHERE rank = 'free'",
            one=True
        )["c"],
        "total_proxies": db.q(
            "SELECT COUNT(*) c FROM proxy_management",
            one=True
        )["c"],
        "total_shopify_sites": db.q(
            "SELECT COUNT(*) c FROM shopify_management",
            one=True
        )["c"],
        "total_stripe_sites": db.q(
            "SELECT COUNT(*) c FROM stripe_management",
            one=True
        )["c"],
    }

# ==============================
# /STATS
# ==============================

async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = update.effective_user.id

    # Permisos: ADMIN o OWNER
    if not (db.is_owner(uid) or db.is_admin(uid)):
        return

    try:
        stats = get_system_stats()
        await msg.reply_text(
            format_stats(stats),
            parse_mode="HTML",
            reply_to_message_id=msg.message_id
        )
    except Exception:
        await msg.reply_text(
            "❌ Error al obtener estadísticas del sistema.",
            reply_to_message_id=msg.message_id
        )

# ==============================
# COMANDOS CON PUNTO
# ==============================

async def handle_dot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == ".stats":
        await handle_stats(update, context)

# ==============================
# REGISTRO
# ==============================

def register_handlers(application):
    application.add_handler(CommandHandler("stats", handle_stats))
    application.add_handler(
        MessageHandler(filters.Regex(r"^\.stats$"), handle_dot)
    )