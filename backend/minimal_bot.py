#!/usr/bin/env python
"""Минимальный работающий Telegram бот для тестирования."""

import os
import sys
import django
import logging
import asyncio
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# НАСТРОЙКА DJANGO ДО ИМПОРТА TELEGRAM
django.setup()

from django.conf import settings
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "🤖 Добро пожаловать в бот фонда «Движение Жизни»!\n\n"
        "Используйте /help для справки."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    await update.message.reply_text(
        "📋 Доступные команды:\n/start - Начать работу\n/help - Справка\n/form - Заполнить анкету"
    )


async def form_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /form"""
    await update.message.reply_text(
        "📝 Начинаем заполнение анкеты...\n\n"
        "Для начала ответьте на несколько вопросов.\n"
        "Как вас зовут?"
    )


def main():
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN не найден")
        return

    try:
        # Явно создаем event loop
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        application = Application.builder().token(token).build()

        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("form", form_command))

        logger.info("🚀 Запуск минимального бота...")
        logger.info("✅ Бот запущен! Проверьте в Telegram: /start")

        # Запускаем с явным указанием event loop
        application.run_polling(
            drop_pending_updates=True,
            close_loop=False
        )

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
