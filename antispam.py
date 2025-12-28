# antispam.py - AntiSpam inteligente por usuario

import time
import db
from telegram import Update
from telegram.ext import ContextTypes

# ==============================
# CONFIG
# ==============================

FREE_LIMIT = 2
FREE_WINDOW = 20

PREMIUM_LIMIT = 4
PREMIUM_WINDOW = 10

# comandos controlados
CONTROLLED_COMMANDS = {"sh", "st", "msh", "mst"}

# user_id -> [timestamps]
USAGE_LOG = {}

# ==============================
# HELPERS
# ==============================

def _get_command_name(update: Update) -> str | None:
    if not update.message or not update.message.text:
        return None

    text = update.message.text.strip().lower()

    if text.startswith("."):
        return text[1:].split()[0]

    if text.startswith("/"):
        return text[1:].split()[0]

    return None


def _clean_old(timestamps: list, window: int) -> list:
    now = time.time()
    return [t for t in timestamps if now - t < window]


# ==============================
# MAIN GUARD
# ==============================

async def antispam_guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user or not update.message:
        return True

    user_id = user.id
    cmd = _get_command_name(update)

    # no comando o no controlado
    if not cmd or cmd not in CONTROLLED_COMMANDS:
        return True

    # owner bypass total
    if db.is_owner(user_id):
        return True

    # determinar rango
    if db.is_admin(user_id) or db.is_premium(user_id):
        limit = PREMIUM_LIMIT
        window = PREMIUM_WINDOW
    else:
        limit = FREE_LIMIT
        window = FREE_WINDOW

    now = time.time()

    timestamps = USAGE_LOG.get(user_id, [])
    timestamps = _clean_old(timestamps, window)

    if len(timestamps) >= limit:
        wait = int(window - (now - timestamps[0]))
        await update.message.reply_text(
            f"⏳ AntiSpam activo\n"
            f"🔒 Espera <b>{wait}s</b> antes de usar otro comando.",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        USAGE_LOG[user_id] = timestamps
        return False

    # registrar uso
    timestamps.append(now)
    USAGE_LOG[user_id] = timestamps
    return True