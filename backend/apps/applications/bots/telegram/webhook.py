"""Вспомогательные функции вебхука для интеграции с Telegram."""

from __future__ import annotations

import asyncio
import json
import logging
from http import HTTPStatus
from typing import Any

from applications.bots.telegram import telegram_bot
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

_initialise_lock = asyncio.Lock()
_application_started = False


async def _ensure_application_ready() -> Any:
    """Лениво инициализирует приложение Telegram для работы вебхука."""

    global _application_started
    async with _initialise_lock:
        application = telegram_bot.application
        if application is None:
            application = telegram_bot.create_webhook_app()
        if not _application_started:
            await application.initialize()
            await application.start()
            _application_started = True
            logger.info("Telegram webhook application initialised")
        return application


@csrf_exempt
async def telegram_webhook(request: HttpRequest) -> HttpResponse:
    """Принимает обновления Telegram и передаёт их приложению PTB."""

    if request.method != "POST":
        return HttpResponse(status=HTTPStatus.METHOD_NOT_ALLOWED)
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON"}, status=HTTPStatus.BAD_REQUEST)
    application = await _ensure_application_ready()
    update_object: Any
    try:
        from telegram import Update as TelegramUpdate  # type: ignore
    except ImportError:
        TelegramUpdate = None  # type: ignore
    if TelegramUpdate is None:
        logger.warning("Телеграм-библиотека не установлена, передаём raw payload")
        update_object = payload
    else:
        try:
            update_object = TelegramUpdate.de_json(payload, application.bot)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Failed to decode Telegram update: %s", exc)
            return JsonResponse({"detail": "Malformed payload"}, status=HTTPStatus.BAD_REQUEST)
    await application.process_update(update_object)
    return HttpResponse(status=HTTPStatus.NO_CONTENT)


__all__ = ["telegram_webhook"]
