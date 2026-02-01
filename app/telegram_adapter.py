from __future__ import annotations

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes, MessageHandler, filters

from app.config import Config
from app.service import FlashcardService


def build_application(config: Config, service: FlashcardService) -> Application:
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_message is None or update.effective_user is None:
            return
        text = update.effective_message.text
        if text is None:
            return
        response = await service.handle_text(text, user_id=update.effective_user.id)
        if response.ignored or not response.message:
            return
        await update.effective_message.reply_text(response.message)

    application = ApplicationBuilder().token(config.telegram_token).build()
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
    return application
