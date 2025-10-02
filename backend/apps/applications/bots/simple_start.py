"""
Минимальная версия для запуска бота
"""

import os
import django
import asyncio
from telegram.ext import Application, CommandHandler

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings


async def start(update, context):
    await update.message.reply_text("🤖 Бот фонда 'Движение Жизни' запущен!\n\nИспользуйте /help для справки")


async def help_command(update, context):
    await update.message.reply_text("📝 Доступные команды:\n/start - начать работу\n/help - справка")


def main():
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN не найден в настройках")
        return

    print("🚀 Запуск бота...")

    try:
        app = Application.builder().token(token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))

        print("✅ Бот запущен! Напишите /start в Telegram")
        app.run_polling()

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
