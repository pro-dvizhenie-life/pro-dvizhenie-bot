"""
Management команда для запуска Telegram бота.
Использование: python manage.py run_telegram_bot
"""

import os
import sys
import signal
from django.core.management.base import BaseCommand
from django.conf import settings


try:
    from ....bots.handlers.telegram_handler import telegram_bot
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("🛠️ Пробуем альтернативный импорт...")
    try:
        # Альтернативный путь
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "telegram_handler",
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "bots", "handlers", "telegram_handler.py")
        )
        telegram_handler = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(telegram_handler)
        telegram_bot = telegram_handler.telegram_bot
    except Exception as e2:
        print(f"❌ Альтернативный импорт тоже не сработал: {e2}")
        raise


class Command(BaseCommand):
    help = 'Запускает Telegram бота в режиме polling'

    def add_arguments(self, parser):
        parser.add_argument(
            '--stop',
            action='store_true',
            help='Остановить бота (в разработке)',
        )

    def handle(self, *args, **options):
        if options['stop']:
            self.stdout.write(
                self.style.WARNING('Остановка бота... (функциональность в разработке)')
            )
            return

        # Проверяем наличие токена
        if not getattr(settings, 'TELEGRAM_BOT_TOKEN', None):
            self.stdout.write(
                self.style.ERROR('❌ TELEGRAM_BOT_TOKEN не найден в настройках Django')
            )
            self.stdout.write(
                self.style.WARNING('Добавьте в settings.py: TELEGRAM_BOT_TOKEN = "ваш_токен"')
            )
            return

        self.stdout.write(
            self.style.SUCCESS('🤖 Запуск Telegram бота...')
        )
        self.stdout.write(
            self.style.WARNING('Для остановки нажмите Ctrl+C')
        )

        # Обработка graceful shutdown
        def signal_handler(sig, frame):
            self.stdout.write(
                self.style.WARNING('\n🛑 Остановка бота...')
            )
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        try:
            # Запускаем бота
            telegram_bot.start_polling()
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('\n🛑 Бот остановлен')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка при запуске бота: {e}')
            )
