import os
import django
from pathlib import Path

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from telegram.ext import Application, CommandHandler


async def start(update, context):
    await update.message.reply_text(
        "🎉 Бот фонда 'Движение Жизни' работает!\n\n"
        "Я помогу вам заполнить заявку на получение помощи.\n\n"
        "Используйте /help для справки"
    )


async def help_command(update, context):
    await update.message.reply_text(
        "📋 Доступные команды:\n"
        "/start - начать работу\n"
        "/help - показать справку\n"
        "/form - начать заполнение анкеты\n\n"
        "💬 Наши специалисты свяжутся с вами после заполнения анкеты."
    )


def main():
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)

    if not token:
        print("❌ TELEGRAM_BOT_TOKEN не найден в настройках Django")
        print("Проверьте .env файл в корне проекта")
        return

    print(f"🚀 Запуск бота: @ProDvizhenie_LifeBot")
    print(f"   Токен: {token[:10]}...")

    try:
        app = Application.builder().token(token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))

        print("✅ Бот запущен!")
        print("📱 Откройте Telegram и напишите /start боту @ProDvizhenie_LifeBot")
        print("⏹️  Для остановки нажмите Ctrl+C")

        app.run_polling()

    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
