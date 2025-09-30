"""Сигналы приложения анкет."""

from __future__ import annotations

import logging

from django.apps import apps
from django.core.management import call_command
from django.db.models.signals import post_migrate
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_migrate)
def ensure_default_survey(sender, **kwargs) -> None:
    """Автоматически создаёт анкету default после первой миграции."""

    if sender is None or getattr(sender, "name", None) != "applications":
        return

    survey_model = apps.get_model("applications", "Survey")
    if survey_model is None:  # pragma: no cover - защитная ветка
        logger.warning("Не удалось получить модель Survey для автозагрузки анкеты.")
        return

    if survey_model.objects.filter(code="default").exists():
        return

    try:
        call_command("load_default_survey")
        logger.info("Команда load_default_survey выполнена автоматически после миграций.")
    except Exception:  # pragma: no cover - логируем сбой, но не рушим миграцию
        logger.exception("Автозагрузка анкеты default завершилась с ошибкой.")
