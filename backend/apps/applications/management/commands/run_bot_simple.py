"""
Упрощенная команда запуска бота с абсолютными путями
"""

import os

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Запускает Telegram бота (упрощенная версия)'

    def handle(self, *args, **options):
        # Проверяем токен
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        if not token:
            self.stdout.write(
                self.style.ERROR('❌ TELEGRAM_BOT_TOKEN не найден')
            )
            return

        self.stdout.write('🤖 Запуск Telegram бота...')

        try:
            # Абсолютный путь к обработчику
            handler_path = os.path.join(
                os.path.dirname(__file__),
                "..", "..", "..", "bots", "handlers", "telegram_handler.py"
            )
            handler_path = os.path.abspath(handler_path)

            if not os.path.exists(handler_path):
                self.stdout.write(
                    self.style.ERROR(f'❌ Файл не найден: {handler_path}')
                )
                return

            # Динамический импорт
            import importlib.util
            spec = importlib.util.spec_from_file_location("telegram_handler", handler_path)
            telegram_handler = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(telegram_handler)

            # Запускаем бота
            telegram_handler.telegram_bot.start_polling()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка: {e}')
            )
            import traceback
            traceback.print_exc()
