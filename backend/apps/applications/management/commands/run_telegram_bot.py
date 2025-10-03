"""
Management команда для запуска Telegram бота.
Использование: python manage.py run_telegram_bot
"""

import signal
import sys

from django.conf import settings
from django.core.management.base import BaseCommand

try:
    from apps.applications.bots.telegram import telegram_bot
except ImportError as e:
    print(f"❌ Ошибка импорта Telegram бота: {e}")
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
