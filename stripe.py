# stripe.py - Gestión de Sitios Stripe (FINAL)

import re
import db
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

# ==============================
# VALIDACIÓN
# ==============================

LIST_PREFIX = re.compile(r"^\s*\d+[\.\-\)]\s*")

def extract_stripe_domain(site: str) -> str:
    if not site:
        return ""

    site = site.strip()

    # ❌ ignora comandos (.ast, /ast, etc.)
    if site.startswith((".", "/")):
        return ""

    # elimina "1. ", "2) ", "3- "
    site = LIST_PREFIX.sub("", site)

    # corrige errores humanos tipo "127https://site.com"
    site = re.sub(r"^\d+", "", site)

    site = site.lower()
    site = site.replace("https://", "").replace("http://", "")
    site = site.replace("www.", "")

    site = site.split("/")[0].split("?")[0].split("#")[0]

    if not site or site.isdigit():
        return ""

    return site if "." in site else ""

def validate_site(raw: str):
    domain = extract_stripe_domain(raw)
    return (True, domain) if domain else (False, "Dominio inválido")

# ==============================
# FORMATOS (IGUALES AL ORIGINAL)
# ==============================

def format_list(sites: list) -> str:
    if not sites:
        return "📭 No hay sitios Stripe registrados."

    body = "\n".join(f"{i}. {s}" for i, s in enumerate(sites, 1))

    return (
        "<b>💳 TUS SITIOS STRIPE</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Total:</b> {len(sites)}/{db.MAX_STRIPE_SITES}\n"
        "━━━━━━━━━━━━━━━━\n"
        f"<pre>{body}</pre>\n"
        "━━━━━━━━━━━━━━━━\n"
        "📝 <b>Uso:</b> <code>/rst NÚMERO</code>"
    )

def format_add(ok, err, total, failed=None):
    text = (
        "<b>📊 RESULTADO</b>\n\n"
        f"✅ Agregados: <b>{ok}</b>\n"
        f"❌ Errores: <b>{err}</b>\n"
        f"📈 Total: <b>{total}</b>/{db.MAX_STRIPE_SITES}"
    )

    if failed:
        text += "\n\n⚠️ <b>Fallidos:</b>"
        for s, r in failed[:5]:
            text += f"\n• {s[:40]} - {r}"
        if len(failed) > 5:
            text += f"\n• … y {len(failed) - 5} más"

    return text

def format_remove(removed, total):
    return (
        "<b>📊 RESULTADO</b>\n\n"
        f"🗑️ Eliminados: <b>{removed}</b>\n"
        f"📈 Total: <b>{total}</b>/{db.MAX_STRIPE_SITES}"
    )

# ==============================
# /AST
# ==============================

async def handle_ast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = update.effective_user.id

    if not db.get_user(uid):
        await msg.reply_text("❌ Debes registrarte primero.", reply_to_message_id=msg.message_id)
        return

    # 👉 mensaje + reply
    text = msg.text or ""
    if msg.reply_to_message and msg.reply_to_message.text:
        text += "\n" + msg.reply_to_message.text

    raw_text = " ".join(text.split()[1:])

    if not raw_text.strip():
        await msg.reply_text(
            "📝 <b>Uso:</b>\n"
            "<code>/ast site1 site2</code>\n"
            "o responde a un mensaje con sitios",
            parse_mode="HTML",
            reply_to_message_id=msg.message_id
        )
        return

    raw_sites = []
    for line in raw_text.splitlines():
        raw_sites.extend(line.split())

    ok = err = 0
    failed = []

    for raw in raw_sites:
        if raw.startswith((".", "/")):
            continue

        if db.check_limit(uid, "stripe_sites"):
            break

        valid, site = validate_site(raw)
        if not valid:
            continue

        success, reason = db.add_user_stripe_site(uid, site)
        if success:
            ok += 1
        else:
            err += 1
            failed.append((raw, reason))

    total = db.count_user_stripe_sites(uid)

    await msg.reply_text(
        format_add(ok, err, total, failed),
        parse_mode="HTML",
        reply_to_message_id=msg.message_id
    )

# ==============================
# /RST
# ==============================

async def handle_rst(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = update.effective_user.id

    if not db.get_user(uid):
        await msg.reply_text("❌ Debes registrarte primero.", reply_to_message_id=msg.message_id)
        return

    sites = db.get_user_stripe_sites(uid)
    if not sites:
        await msg.reply_text("📭 No tienes sitios Stripe.", reply_to_message_id=msg.message_id)
        return

    # 👉 mensaje + reply
    text = msg.text or ""
    if msg.reply_to_message and msg.reply_to_message.text:
        text += "\n" + msg.reply_to_message.text

    raw_input = " ".join(text.split()[1:])

    if not raw_input.strip():
        await msg.reply_text(
            format_list(sites),
            parse_mode="HTML",
            reply_to_message_id=msg.message_id
        )
        return

    removed = 0

    for token in raw_input.split():
        if token.startswith((".", "/")):
            continue

        if token.isdigit() and not msg.reply_to_message:
            idx = int(token) - 1
            if 0 <= idx < len(sites):
                db.remove_user_stripe_site(uid, sites[idx])
                removed += 1
                sites = db.get_user_stripe_sites(uid)
        else:
            key = extract_stripe_domain(token)
            for s in sites:
                if key and key in s:
                    db.remove_user_stripe_site(uid, s)
                    removed += 1
                    sites = db.get_user_stripe_sites(uid)
                    break

    total = db.count_user_stripe_sites(uid)

    await msg.reply_text(
        format_remove(removed, total),
        parse_mode="HTML",
        reply_to_message_id=msg.message_id
    )

# ==============================
# /SST
# ==============================

async def handle_sst(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = update.effective_user.id

    if not db.get_user(uid):
        await msg.reply_text("❌ Debes registrarte primero.", reply_to_message_id=msg.message_id)
        return

    await msg.reply_text(
        format_list(db.get_user_stripe_sites(uid)),
        parse_mode="HTML",
        reply_to_message_id=msg.message_id
    )

# ==============================
# /DST
# ==============================

async def handle_dst(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = update.effective_user.id

    if not db.get_user(uid):
        await msg.reply_text("❌ Debes registrarte primero.", reply_to_message_id=msg.message_id)
        return

    total = db.count_user_stripe_sites(uid)
    if total == 0:
        await msg.reply_text("📭 No hay sitios para eliminar.", reply_to_message_id=msg.message_id)
        return

    db.clear_user_stripe_sites(uid)

    await msg.reply_text(
        f"✅ Eliminados <b>{total}</b> sitios Stripe.",
        parse_mode="HTML",
        reply_to_message_id=msg.message_id
    )

# ==============================
# DOT
# ==============================

async def handle_dot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text.startswith(".ast"):
        await handle_ast(update, context)
    elif text.startswith(".rst"):
        await handle_rst(update, context)
    elif text == ".sst":
        await handle_sst(update, context)
    elif text == ".dst":
        await handle_dst(update, context)

# ==============================
# REGISTER
# ==============================

def register_handlers(application):
    application.add_handler(CommandHandler("ast", handle_ast))
    application.add_handler(CommandHandler("rst", handle_rst))
    application.add_handler(CommandHandler("sst", handle_sst))
    application.add_handler(CommandHandler("dst", handle_dst))
    application.add_handler(
        MessageHandler(filters.Regex(r"^\.(ast|rst|sst|dst)\b"), handle_dot)
    )