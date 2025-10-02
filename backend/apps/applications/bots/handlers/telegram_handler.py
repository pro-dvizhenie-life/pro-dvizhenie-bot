"""Основной обработчик Telegram бота."""

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from django.conf import settings

# Настройка логирования
logger = logging.getLogger(__name__)

# Импорты наших обработчиков
from .telegram_handlers.start import start
from .telegram_handlers.help import help_command
from .telegram_handlers.form import form_entry, handle_callback, handle_text
from .telegram_handlers.preview import handle_preview_callback
from .telegram_handlers.documents import handle_documents

class TelegramBot:
    def __init__(self):
        self.token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        self.application = None

        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN не найден в настройках Django")

    def setup_handlers(self):
        """Настройка обработчиков бота."""

        # 1. КОМАНДЫ
        self.application.add_handler(CommandHandler("start", start))
        self.application.add_handler(CommandHandler("help", help_command))
        self.application.add_handler(CommandHandler("form", form_entry))
        self.application.add_handler(CommandHandler("anketa", form_entry))  # Альтернативная команда

        # 2. CALLBACK-ЗАПРОСЫ (нажатия на кнопки)
        # Группируем похожие callback'ы для эффективности
        self.application.add_handler(CallbackQueryHandler(
            handle_callback,
            pattern="^(YES|NO|APPLICANT_|GENDER_|PRODUCT_|CONSULT_)"
        ))
        self.application.add_handler(CallbackQueryHandler(
            handle_preview_callback,
            pattern="^(RESUME_BUTTON|RESTART_BUTTON)"
        ))

        # 3. ТЕКСТОВЫЕ СООБЩЕНИЯ (исключая команды)
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text
        ))

        # 4. ДОКУМЕНТЫ И ФОТО (разделяем для точности)
        self.application.add_handler(MessageHandler(
            filters.PHOTO,
            handle_documents
        ))
        self.application.add_handler(MessageHandler(
            filters.Document.ALL,
            handle_documents
        ))

        # 5. ОБРАБОТЧИК ОШИБОК
        self.application.add_error_handler(self.error_handler)

        logger.info("✅ Все обработчики Telegram бота настроены")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Глобальный обработчик ошибок бота."""
        logger.error(f"❌ Ошибка в боте: {context.error}", exc_info=True)

        # Уведомляем пользователя об ошибке
        if update and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="😕 Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже или обратитесь в поддержку."
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение об ошибке: {e}")

    def start_polling(self):
        """Запуск бота в режиме polling."""
        if not self.token:
            raise ValueError("❌ TELEGRAM_BOT_TOKEN не настроен. Добавьте в settings.py")

        try:
            self.application = Application.builder().token(self.token).build()
            self.setup_handlers()

            logger.info("🚀 Telegram бот запускается в режиме polling...")

            # Запускаем polling с настройками
            self.application.run_polling(
                drop_pending_updates=True,  # Игнорируем старые сообщения при запуске
                allowed_updates=Update.ALL_TYPES,
                close_loop=False  # Важно для интеграции с Django
            )

        except Exception as e:
            logger.error(f"❌ Ошибка при запуске бота: {e}")
            raise

    def create_webhook_app(self):
        """
        Создание приложения для webhook режима.
        Для использования в production.
        """
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN не настроен")

        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()

        logger.info("🌐 Webhook приложение создано")
        return self.application

# Глобальный экземпляр бота
telegram_bot = TelegramBot()