#!/usr/bin/env python
"""Запуск Telegram бота вместе с Django."""

import os
import sys
import django
import logging
from pathlib import Path

# Настройка пути к Django проекту
BASE_DIR = Path(__file__).resolve().parent  # backend/
PROJECT_ROOT = BASE_DIR.parent  # корень проекта (pro-dvizhenie-bot/)

# Добавляем в Python path
sys.path.insert(0, str(BASE_DIR))


# Загружаем .env вручную перед настройкой Django
def load_env(env_path: Path) -> None:
    """Загружает переменные из .env файла."""
    if not env_path.exists():
        print(f"❌ Файл .env не найден: {env_path}")
        return

    for line in env_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


# Загружаем .env
env_path = PROJECT_ROOT / '.env'
load_env(env_path)

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    django.setup()
    print("✅ Django настроен")
except Exception as e:
    print(f"❌ Ошибка настройки Django: {e}")
    sys.exit(1)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger(__name__)


def main():
    """Основная функция запуска бота."""
    try:
        logger.info("🚀 Запуск Telegram бота...")

        # Проверяем наличие токена
        from django.conf import settings
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)

        if not token:
            logger.error("❌ TELEGRAM_BOT_TOKEN не найден в настройках Django")
            return

        logger.info(f"✅ Токен бота загружен: {token[:10]}...")

        # Проверяем установку python-telegram-bot
        try:
            from telegram import __version__ as telegram_version
            logger.info(f"✅ python-telegram-bot версия: {telegram_version}")
        except ImportError as e:
            logger.error("❌ python-telegram-bot не установлен")
            return

        # Импортируем бота - ТЕПЕРЬ ПРАВИЛЬНЫЙ ПУТЬ
        try:
            from apps.applications.bots.handlers.telegram_handlers.telegram_handler import telegram_bot
            logger.info("✅ Бот успешно импортирован")
        except ImportError as e:
            logger.error(f"❌ Ошибка импорта бота: {e}")
            return

        # Запускаем бота
        logger.info("✅ Запускаем бота в режиме polling...")
        telegram_bot.start_polling()

    except KeyboardInterrupt:
        logger.info("⏹️  Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}", exc_info=True)


if __name__ == '__main__':
    main()
