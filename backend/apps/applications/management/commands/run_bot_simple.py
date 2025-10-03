"""Упрощённая команда запуска Telegram бота."""

from apps.applications.bots.telegram import telegram_bot
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Запускает Telegram бота (упрощённый запуск)'

    def handle(self, *args, **options):
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        if not token:
            self.stdout.write(self.style.ERROR('❌ TELEGRAM_BOT_TOKEN не найден'))
            return

        self.stdout.write('🤖 Запуск Telegram бота...')
        try:
            telegram_bot.start_polling()
        except Exception as exc:  # pragma: no cover - диагностический вывод
            self.stdout.write(self.style.ERROR(f'❌ Ошибка: {exc}'))
            import traceback

            traceback.print_exc()
