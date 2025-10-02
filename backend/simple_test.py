#!/usr/bin/env python3
"""
Простейший тест бота
"""

import os
import sys

# Проверяем установку telegram
try:
    from telegram.ext import Application, CommandHandler

    print("✅ python-telegram-bot импортирован успешно!")
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("🛠️  Установите: pip install python-telegram-bot==20.7")
    sys.exit(1)

# Проверяем токен
token = "8453441805:AAGQdyao8VAm1ng4nbcqJ-04wiDYCkIy6lA"  # ваш токен

if not token or token == "ВАШ_ТОКЕН_ЗДЕСЬ":
    print("❌ Укажите токен бота")
    sys.exit(1)

print(f"🚀 Тестовый запуск бота с токеном: {token[:10]}...")


async def start(update, context):
    await update.message.reply_text("✅ Тестовый бот работает!")


def main():
    try:
        app = Application.builder().token(token).build()
        app.add_handler(CommandHandler("start", start))

        print("✅ Бот запускается...")
        print("📱 Напишите /start в Telegram боту @ProDvizhenie_LifeBot")
        print("⏹️  Ctrl+C для остановки")

        app.run_polling()

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()