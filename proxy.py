# proxy.py - Proxy Manager (FINAL DEFINITIVO + HTTPBIN)

import re
import time
import requests
import db
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

# ==============================
# NORMALIZACIÓN
# ==============================

def normalize_proxy(proxy: str) -> str:
    proxy = proxy.strip()
    proxy = proxy.replace("http://", "").replace("https://", "")
    proxy = proxy.replace("socks5://", "").replace("socks4://", "")
    proxy = proxy.replace("socks5h://", "").replace("socks4a://", "")

    # user:pass@host:port -> host:port:user:pass
    if "@" in proxy:
        auth, host = proxy.split("@", 1)
        if ":" in auth and ":" in host:
            user, pwd = auth.split(":", 1)
            ip, port = host.split(":", 1)
            return f"{ip}:{port}:{user}:{pwd}"

    return proxy

# ==============================
# VALIDACIÓN ESTRICTA
# ==============================

def validate_proxy(proxy: str):
    parts = proxy.split(":")
    if len(parts) != 4:
        return False, "Formato inválido (host:port:user:pass)"

    host, port, user, pwd = parts

    if not host or not user or not pwd:
        return False, "Datos incompletos"

    try:
        port = int(port)
        if not (1 <= port <= 65535):
            return False, "Puerto inválido"
    except Exception:
        return False, "Puerto inválido"

    return True, proxy

# ==============================
# CHECK REAL (HTTPBIN)
# ==============================

def check_proxy_httpbin(proxy: str, timeout=10):
    try:
        host, port, user, pwd = proxy.split(":")
        proxy_url = f"http://{user}:{pwd}@{host}:{port}"

        proxies = {
            "http": proxy_url,
            "https": proxy_url,
        }

        start = time.time()
        r = requests.get(
            "http://httpbin.org/ip",
            proxies=proxies,
            timeout=timeout,
            verify=False
        )
        elapsed = time.time() - start

        if r.status_code == 200:
            return True, f"OK ({elapsed:.2f}s)"

        if r.status_code == 407:
            return False, "Auth inválida"

        return False, f"HTTP {r.status_code}"

    except requests.exceptions.ProxyError:
        return False, "Proxy error"
    except requests.exceptions.ConnectTimeout:
        return False, "Timeout"
    except requests.exceptions.ConnectionError:
        return False, "Sin conexión"
    except Exception as e:
        return False, str(e)[:40]

# ==============================
# INPUT
# ==============================

def extract_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = msg.text
    is_dot = text.startswith(".")

    if is_dot:
        raw = " ".join(text.split()[1:])
    elif context.args:
        raw = " ".join(context.args)
    elif msg.reply_to_message:
        raw = msg.reply_to_message.text
    else:
        raw = ""

    return [x for x in re.split(r"\s+", raw) if x]

# ==============================
# FORMATOS
# ==============================

def format_list(proxies: list) -> str:
    if not proxies:
        return "📭 No tienes proxies."

    body = "\n".join(f"{i}. {p}" for i, p in enumerate(proxies, 1))

    return (
        "<b>🔌 TUS PROXIES</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Total:</b> {len(proxies)}/{db.MAX_PROXIES}\n"
        "━━━━━━━━━━━━━━━━\n"
        f"<pre>{body}</pre>\n"
        "━━━━━━━━━━━━━━━━\n"
        "📝 <b>Uso:</b> <code>/remove NÚMERO</code> o <code>/remove PROXY_COMPLETA</code>"
    )

def format_add(ok, err, total, failed):
    text = (
        "<b>📊 RESULTADO</b>\n\n"
        f"✅ Agregadas: <b>{ok}</b>\n"
        f"❌ Rechazadas: <b>{err}</b>\n"
        f"📈 Total: <b>{total}</b>/{db.MAX_PROXIES}"
    )

    if failed:
        text += "\n\n⚠️ <b>Fallidas:</b>"
        for p, r in failed[:5]:
            text += f"\n• {p} - {r}"
        if len(failed) > 5:
            text += f"\n• … y {len(failed) - 5} más"

    return text

def format_remove(removed, total):
    return (
        "<b>📊 RESULTADO</b>\n\n"
        f"🗑️ Eliminadas: <b>{removed}</b>\n"
        f"📈 Total: <b>{total}</b>/{db.MAX_PROXIES}"
    )

# ==============================
# /ADD
# ==============================

async def handle_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = update.effective_user.id

    if not db.get_user(uid):
        await msg.reply_text("❌ Debes registrarte primero.", reply_to_message_id=msg.message_id)
        return

    items = extract_items(update, context)
    if not items:
        await msg.reply_text(
            "📝 <b>Uso:</b>\n"
            "<code>/add host:port:user:pass</code>",
            parse_mode="HTML",
            reply_to_message_id=msg.message_id
        )
        return

    ok = err = 0
    failed = []

    for raw in items:
        if db.check_limit(uid, "proxies"):
            break

        proxy = normalize_proxy(raw)
        valid, result = validate_proxy(proxy)
        if not valid:
            err += 1
            failed.append((raw, result))
            continue

        alive, reason = check_proxy_httpbin(proxy)
        if not alive:
            err += 1
            failed.append((raw, reason))
            continue

        success, reason = db.add_user_proxy(uid, proxy)
        if success:
            ok += 1
        else:
            err += 1
            failed.append((raw, reason))

    total = db.count_user_proxies(uid)

    await msg.reply_text(
        format_add(ok, err, total, failed),
        parse_mode="HTML",
        reply_to_message_id=msg.message_id
    )

# ==============================
# /REMOVE (EXACTO)
# ==============================

async def handle_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = update.effective_user.id

    proxies = db.get_user_proxies(uid)
    if not proxies:
        await msg.reply_text("📭 No tienes proxies.", reply_to_message_id=msg.message_id)
        return

    items = extract_items(update, context)
    if not items:
        await msg.reply_text(format_list(proxies), parse_mode="HTML", reply_to_message_id=msg.message_id)
        return

    removed = 0

    for item in items:
        if item.isdigit():
            idx = int(item) - 1
            if 0 <= idx < len(proxies):
                db.remove_user_proxy(uid, proxies[idx])
                removed += 1
                proxies = db.get_user_proxies(uid)
        else:
            if item in proxies:
                db.remove_user_proxy(uid, item)
                removed += 1
                proxies = db.get_user_proxies(uid)

    total = db.count_user_proxies(uid)

    await msg.reply_text(
        format_remove(removed, total),
        parse_mode="HTML",
        reply_to_message_id=msg.message_id
    )

# ==============================
# /SHOW
# ==============================

async def handle_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text(
        format_list(db.get_user_proxies(uid)),
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )

# ==============================
# /DELETE
# ==============================

async def handle_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    total = db.count_user_proxies(uid)

    if total == 0:
        await update.message.reply_text("📭 No tienes proxies.", reply_to_message_id=update.message.message_id)
        return

    db.clear_user_proxies(uid)
    await update.message.reply_text(
        f"✅ Eliminadas <b>{total}</b> proxies.",
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )

# ==============================
# DOT
# ==============================

async def handle_dot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    if t.startswith(".add"):
        await handle_add(update, context)
    elif t.startswith(".remove"):
        await handle_remove(update, context)
    elif t == ".show":
        await handle_show(update, context)
    elif t == ".delete":
        await handle_delete(update, context)

# ==============================
# REGISTER
# ==============================

def register_handlers(application):
    application.add_handler(CommandHandler("add", handle_add))
    application.add_handler(CommandHandler("remove", handle_remove))
    application.add_handler(CommandHandler("show", handle_show))
    application.add_handler(CommandHandler("delete", handle_delete))
    application.add_handler(
        MessageHandler(filters.Regex(r"^\.(add|remove|show|delete)\b"), handle_dot)
    )