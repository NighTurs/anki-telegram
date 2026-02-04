from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes, MessageHandler, filters

from app.config import Config
from app.service import FlashcardService

logger = logging.getLogger(__name__)


def build_application(config: Config, service: FlashcardService) -> Application:
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_message is None or update.effective_user is None:
            return
        text = update.effective_message.text
        if text is None:
            return
        logger.info("Telegram message received (user_id=%s)", update.effective_user.id)
        response = await service.handle_text(text, user_id=update.effective_user.id)
        if response.ignored or not response.message:
            return
        logger.info("Telegram response sending (user_id=%s)", update.effective_user.id)
        await update.effective_message.reply_text(response.message)

    application = ApplicationBuilder().token(config.telegram_token).build()
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
    return application
