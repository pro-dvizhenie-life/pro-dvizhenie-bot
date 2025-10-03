"""Тесты webhook-а Telegram."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from django.test import SimpleTestCase


class TelegramWebhookTests(SimpleTestCase):
    """Проверяет обработку входящих запросов Telegram."""

    path = "/api/v1/applications/telegram/webhook/"

    def test_method_not_allowed(self):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 405)

    def test_rejects_invalid_json(self):
        response = self.client.post(
            self.path,
            data="not-json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_processes_valid_update(self):
        fake_application = SimpleNamespace(bot=None, process_update=AsyncMock())
        payload = {"update_id": 101}
        with patch(
            "applications.bots.telegram.webhook._ensure_application_ready",
            new=AsyncMock(return_value=fake_application),
        ):
            response = self.client.post(
                self.path,
                data=json.dumps(payload),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(fake_application.process_update.await_count, 1)
