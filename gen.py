# gen.py - Card Generator (FINAL · FORMATO ORIGINAL · COPIABLE)

import random
import datetime
import re
import db
from bin import get_bin_info
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

BOT_TAG = '<a href="http://t.me/SaitamaChecker_Bot">[拳]</a>'

# ==============================
# LUHN
# ==============================

def luhn_digit(num: str) -> int:
    total = 0
    for i, d in enumerate(num[::-1]):
        n = int(d)
        if i % 2 == 0:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return (10 - total % 10) % 10


# ==============================
# CARD
# ==============================

def generate_card(bin_pattern: str) -> str:
    digits = []
    for c in bin_pattern:
        if c.lower() == "x":
            digits.append(str(random.randint(0, 9)))
        elif c.isdigit():
            digits.append(c)

    info = get_bin_info("".join(digits[:6]))
    brand = (info or {}).get("info", "").lower()

    length = 16
    if "amex" in brand or "american express" in brand:
        length = 15
    elif "diners" in brand:
        length = 14

    digits = digits[:length - 1]
    while len(digits) < length - 1:
        digits.append(str(random.randint(0, 9)))

    return "".join(digits) + str(luhn_digit("".join(digits)))


# ==============================
# DATE (YYYY)
# ==============================

def generate_date(mm=None, yy=None):
    now = datetime.datetime.now()

    month = random.randint(1, 12) if not mm or "x" in mm.lower() else max(1, min(12, int(mm)))
    year = now.year + random.randint(1, 10) if not yy or "x" in yy.lower() else int(yy)

    if year < 100:
        year += (now.year // 100) * 100
        if year < now.year:
            year += 100

    return f"{month:02d}", f"{year}"


# ==============================
# CVV
# ==============================

def generate_cvv(card: str, pattern=None):
    info = get_bin_info(card[:6])
    brand = (info or {}).get("info", "").lower()
    size = 4 if "amex" in brand else 3

    if not pattern or "x" in pattern.lower():
        return "".join(str(random.randint(0, 9)) for _ in range(size))

    digits = [c for c in pattern if c.isdigit()]
    while len(digits) < size:
        digits.append(str(random.randint(0, 9)))

    return "".join(digits[:size])


# ==============================
# /GEN
# ==============================

async def handle_gen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = update.effective_user.id
    user = update.effective_user.username or update.effective_user.first_name

    if not db.get_user(uid):
        await msg.reply_text(
            "❌ Debes registrarte primero.",
            reply_to_message_id=msg.message_id
        )
        return

    if not context.args:
        await msg.reply_text(
            "⚠️ Uso:\n<code>/gen BIN|MM|YY|CVV</code>",
            parse_mode="HTML",
            reply_to_message_id=msg.message_id
        )
        return

    raw = context.args[0]
    parts = raw.split("|")

    bin_pattern = parts[0]
    mm = parts[1] if len(parts) > 1 else None
    yy = parts[2] if len(parts) > 2 else None
    cvv = parts[3] if len(parts) > 3 else None

    bin_digits = re.sub(r"\D", "", bin_pattern)[:6]
    info = get_bin_info(bin_digits)

    if not info or not info.get("success"):
        await msg.reply_text(
            "❌ BIN inválido.",
            reply_to_message_id=msg.message_id
        )
        return

    cards = []
    for _ in range(10):
        cc = generate_card(bin_pattern)
        m, y = generate_date(mm, yy)
        c = generate_cvv(cc, cvv)
        cards.append(f"<code>{cc}|{m}|{y}|{c}</code>")

    text = (
        f"{BOT_TAG} <b>Card Generator</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        + "\n".join(cards) + "\n"
        "━━━━━━━━━━━━━━━━\n"
        f"{BOT_TAG} <b>Info:</b> <code>{info['info']}</code>\n"
        f"{BOT_TAG} <b>Bank:</b> <code>{info['bank']}</code>\n"
        f"{BOT_TAG} <b>Country:</b> <code>{info['country']}</code>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"{BOT_TAG} <b>Req by:</b> @{user}"
    )

    await msg.reply_text(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_to_message_id=msg.message_id
    )


# ==============================
# DOT
# ==============================

async def handle_dot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.startswith(".gen"):
        context.args = update.message.text.split()[1:]
        await handle_gen(update, context)


# ==============================
# REGISTER
# ==============================

def register_handlers(app):
    app.add_handler(CommandHandler("gen", handle_gen))
    app.add_handler(MessageHandler(filters.Regex(r"^\.gen\b"), handle_dot))