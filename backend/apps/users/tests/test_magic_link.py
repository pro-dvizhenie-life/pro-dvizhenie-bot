"""Тесты сценария входа по магической ссылке."""

from __future__ import annotations

import re

from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import MagicLinkToken, User
from users.services import issue_magic_link_and_send_email


class MagicLinkFlowTests(APITestCase):
    """Проверяем рассылку и использование magic link."""

    def setUp(self) -> None:
        self.register_url = reverse("register")
        self.magic_login_url = reverse("magic-link-login")
        self.magic_request_url = reverse("magic-link-request")

    def test_register_sends_magic_link_email(self) -> None:
        response = self.client.post(
            self.register_url,
            {
                "email": "applicant@example.com",
                "phone": "+70000000000",
                "password": "StrongPass123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(MagicLinkToken.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

        body = mail.outbox[0].body
        match = re.search(r"token=([A-Za-z0-9_\-]+)", body)
        self.assertIsNotNone(match, "Email should contain resume token")
        raw_token = match.group(1)

        token = MagicLinkToken.objects.get(user__email="applicant@example.com")
        verified_token = MagicLinkToken.objects.verify(raw_token)
        self.assertIsNotNone(verified_token)
        self.assertEqual(token.pk, verified_token.pk)

    def test_magic_link_login_exchanges_token_for_tokens(self) -> None:
        user = User.objects.create_user(
            email="applicant@example.com",
            phone="+70000000000",
            password="StrongPass123",
        )
        result = issue_magic_link_and_send_email(user)

        response = self.client.post(
            self.magic_login_url,
            {"token": result.raw_token},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], user.email)

        token = result.token
        token.refresh_from_db()
        self.assertIsNotNone(token.used_at)

    def test_magic_link_login_rejects_invalid_token(self) -> None:
        response = self.client.post(
            self.magic_login_url,
            {"token": "nonexistent"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_magic_link_request_sends_email_without_leaking_user(self) -> None:
        user = User.objects.create_user(
            email="applicant@example.com",
            phone="+70000000000",
            password="StrongPass123",
        )
        mail.outbox.clear()

        response = self.client.post(
            self.magic_request_url,
            {"email": user.email},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(mail.outbox), 1)

        response = self.client.post(
            self.magic_request_url,
            {"email": "unknown@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(mail.outbox), 1)
