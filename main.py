# main.py - Launcher principal de SaitamaChk

import logging
import asyncio

from telegram.ext import Application

# ==============================
# CONFIG
# ==============================

BOT_TOKEN = "8319878167:AAEawgnyUMk7U23e-QjggbkR4FchFmy71aQ"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

log = logging.getLogger("SaitamaChk")

# ==============================
# IMPORT MODULES
# ==============================

import db

import start
import cmds
import panel

import promote
import addpremium
import stats
import broadcast

import info
import bin
import gen

import proxy
import shopify
import stripe

import check
import csh
import cst

import sh
import st
import msh
import mst

# ==============================
# ERROR HANDLER
# ==============================

async def error_handler(update, context):
    log.error("Unhandled exception", exc_info=context.error)

    try:
        if update and update.message:
            await update.message.reply_text(
                "❌ Ocurrió un error inesperado.",
                reply_to_message_id=update.message.message_id
            )
    except Exception:
        pass

# ==============================
# MAIN
# ==============================

def main():
    log.info("🚀 Iniciando SaitamaChk...")

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .build()
    )

    # ==========================
    # REGISTER HANDLERS
    # ==========================

    start.register_handlers(application)
    cmds.register_handlers(application)
    panel.register_handlers(application)

    promote.register_handlers(application)
    addpremium.register_handlers(application)
    stats.register_handlers(application)
    broadcast.register_handlers(application)

    info.register_handlers(application)
    bin.register_handlers(application)
    gen.register_handlers(application)

    proxy.register_handlers(application)
    shopify.register_handlers(application)
    stripe.register_handlers(application)

    check.register_handlers(application)
    csh.register_handlers(application)
    cst.register_handlers(application)

    sh.register_handlers(application)
    st.register_handlers(application)
    msh.register_handlers(application)
    mst.register_handlers(application)

    # ==========================
    # ERROR HANDLER
    # ==========================

    application.add_error_handler(error_handler)

    log.info("✅ Todos los handlers registrados correctamente")

    # ==========================
    # START BOT
    # ==========================

    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"]
    )

# ==============================
# ENTRY
# ==============================

if __name__ == "__main__":
    main()