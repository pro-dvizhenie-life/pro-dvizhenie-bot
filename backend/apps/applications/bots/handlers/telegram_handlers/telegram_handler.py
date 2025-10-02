"""Telegram bot entry-point wiring scenario handlers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from applications.bots.scenarios.default_scenario import DefaultScenario
from django.conf import settings

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from telegram.ext import ContextTypes


def _require_ptb_components():
    try:
        from telegram import Update
        from telegram.ext import (
            Application,
            CallbackQueryHandler,
            CommandHandler,
            MessageHandler,
            filters,
        )
    except ImportError as exc:  # pragma: no cover - dependency absent only in tests
        raise RuntimeError("python-telegram-bot не установлен") from exc
    return Update, Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters


class TelegramBot:
    """Configures telegram-ext application and delegates to the scenario."""

    def __init__(self) -> None:
        self.token: Optional[str] = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        self.application = None
        self.scenario = DefaultScenario()
        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN не найден в настройках Django")

    def setup_handlers(self) -> None:
        if self.application is None:
            raise RuntimeError("Application instance is not initialised")
        _, _, CallbackQueryHandler, CommandHandler, MessageHandler, filters = _require_ptb_components()
        scenario = self.scenario
        self.application.add_handler(CommandHandler("start", scenario.handle_start))
        self.application.add_handler(CommandHandler("help", scenario.handle_help))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, scenario.handle_text)
        )
        self.application.add_handler(CallbackQueryHandler(scenario.handle_callback))
        document_filters = (
            filters.Document.ALL
            | filters.PHOTO
            | filters.AUDIO
            | filters.VIDEO
            | filters.VIDEO_NOTE
        )
        self.application.add_handler(MessageHandler(document_filters, scenario.handle_document))
        self.application.add_error_handler(self.error_handler)
        logger.info("Telegram handlers configured")

    async def error_handler(self, update: object, context: "ContextTypes.DEFAULT_TYPE") -> None:
        update_payload = update.to_dict() if hasattr(update, "to_dict") else repr(update)
        logger.exception(
            "Ошибка в Telegram боте: %s | update=%s",
            getattr(context, "error", None),
            update_payload,
        )
        chat = getattr(update, "effective_chat", None)
        chat_id = getattr(chat, "id", None)
        if chat_id:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Произошла ошибка. Попробуйте ещё раз или свяжитесь с поддержкой.",
                )
            except Exception:  # pragma: no cover - best-effort notification
                logger.debug("Не удалось уведомить пользователя об ошибке", exc_info=True)

    def _build_application(self) -> None:
        _, ApplicationCls, *_ = _require_ptb_components()
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN не настроен")
        self.application = ApplicationCls.builder().token(self.token).build()

    def start_polling(self) -> None:
        Update, *_ = _require_ptb_components()
        self._build_application()
        self.setup_handlers()
        logger.info("Запускаем Telegram бота в режиме polling")
        assert self.application is not None
        self.application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
            close_loop=False,
        )

    def create_webhook_app(self):
        self._build_application()
        self.setup_handlers()
        logger.info("Webhook-приложение Telegram собрано")
        return self.application


telegram_bot = TelegramBot()


__all__ = ["TelegramBot", "telegram_bot"]
