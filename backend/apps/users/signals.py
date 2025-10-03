"""Сигнал для автосоздания суперпользователя.

Подробнее о механизме сигналов:
https://docs.djangoproject.com/en/stable/topics/signals/

Что делает этот сигнал?
-----------------------
Мы подписываемся на событие `post_migrate`, которое срабатывает после
применения миграций.
Обработчик `ensure_initial_superuser` проверяет, нужно ли создать
суперпользователя (берёт данные из переменных окружения) и создаёт его,
если он отсутствует.

Алгоритм работы:
----------------
1. Проверяем флаг окружения `DJANGO_SUPERUSER_CREATE` (по умолчанию True).
2. Читаем `DJANGO_SUPERUSER_EMAIL` и `DJANGO_SUPERUSER_PASSWORD`.
3. Если они заданы и такого пользователя ещё нет — создаём суперпользователя.
4. В логах фиксируется результат.
"""

from __future__ import annotations

import logging
import os

from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _str_to_bool(value: str | None, default: bool) -> bool:
    """Интерпретирует строку как булево значение с поддержкой флагов окружения."""

    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


@receiver(post_migrate)
def ensure_initial_superuser(sender, app_config, using, **kwargs) -> None:
    """Создаёт первоначального суперпользователя после миграций,
    если это разрешено в окружении."""

    if app_config.label != 'users':
        return

    should_create = _str_to_bool(os.environ.get(
        'DJANGO_SUPERUSER_CREATE',
        'true'), True
    )
    if not should_create:
        logger.debug(
            'Skipping auto superuser creation because flag is disabled'
        )
        return

    email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

    if not email or not password:
        logger.debug(
            'Superuser email/password not provided; skipping auto creation'
        )
        return

    user_model = get_user_model()
    manager = user_model.objects.db_manager(using)

    if manager.filter(email=email).exists():
        return

    phone = os.environ.get('DJANGO_SUPERUSER_PHONE')
    if not phone:
        logger.debug(
            'Superuser phone not provided; skipping auto creation'
        )
        return

    extra_fields = {'phone': phone}

    try:
        manager.create_superuser(
            email=email,
            password=password,
            **extra_fields,
        )
        logger.info('Created initial superuser with email %s', email)
    except Exception:  # pragma: no cover - defensive logging
        logger.exception('Failed to create the initial superuser')
