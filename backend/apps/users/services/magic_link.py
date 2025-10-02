"""Функции для генерации и отправки magic link токенов."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from config.constants import (
    MAGIC_LINK_DEFAULT_EMAIL_SUBJECT,
    MAGIC_LINK_DEFAULT_RESUME_URL,
    MAGIC_LINK_DEFAULT_TTL_MINUTES,
    MAGIC_LINK_TOKEN_RAW_BYTES,
)
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import TemplateDoesNotExist, render_to_string
from django.utils import timezone

from ..models import MagicLinkToken, User


@dataclass(frozen=True)
class MagicLinkIssueResult:
    """Результат генерации magic link."""

    token: MagicLinkToken
    raw_token: str
    resume_url: str


def _generate_raw_token() -> tuple[str, str]:
    """Возвращает пару (raw_token, hashed_token)."""

    raw_token = secrets.token_urlsafe(MAGIC_LINK_TOKEN_RAW_BYTES)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    return raw_token, token_hash


def _token_expiration() -> datetime:
    """Вычисляет момент истечения токена magic link."""

    ttl_minutes = getattr(settings, "MAGIC_LINK_TOKEN_TTL_MINUTES", MAGIC_LINK_DEFAULT_TTL_MINUTES)
    return timezone.now() + timedelta(minutes=ttl_minutes)


def _build_resume_url(raw_token: str) -> str:
    """Формирует ссылку на продолжение заявки с токеном входа."""

    base_url = getattr(
        settings,
        "FRONTEND_APPLICATION_RESUME_URL",
        MAGIC_LINK_DEFAULT_RESUME_URL,
    ).rstrip("/")
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}token={raw_token}"


def _render_email(template: str, context: dict[str, object]) -> str:
    """Рендерит письмо по шаблону, возвращая пустую строку при отсутствии."""

    try:
        return render_to_string(template, context)
    except TemplateDoesNotExist:
        return ""


def issue_magic_link_and_send_email(user: User) -> MagicLinkIssueResult:
    """Создаёт новый токен, отправляет письмо и возвращает данные."""

    with transaction.atomic():
        MagicLinkToken.objects.filter(
            user=user,
            used_at__isnull=True,
            expires_at__lte=timezone.now(),
        ).delete()
        raw_token, token_hash = _generate_raw_token()
        token = MagicLinkToken.objects.create(
            user=user,
            token_hash=token_hash,
            expires_at=_token_expiration(),
        )
    resume_url = _build_resume_url(raw_token)
    context = {
        "user": user,
        "resume_url": resume_url,
        "token_valid_minutes": getattr(
            settings,
            "MAGIC_LINK_TOKEN_TTL_MINUTES",
            MAGIC_LINK_DEFAULT_TTL_MINUTES,
        ),
        "project_name": getattr(settings, "PROJECT_NAME", "Про Движение"),
    }
    subject = getattr(
        settings,
        "MAGIC_LINK_EMAIL_SUBJECT",
        MAGIC_LINK_DEFAULT_EMAIL_SUBJECT,
    )
    text_body = _render_email("emails/magic_link_login.txt", context)
    html_body = _render_email("emails/magic_link_login.html", context)
    send_mail(
        subject=subject,
        message=text_body or (
            "Здравствуйте!\n\n"
            "Вы начинали заполнять заявку в проекте 'Про Движение'. "
            "Перейдите по ссылке ниже, чтобы вернуться и завершить её:\n"
            f"{resume_url}\n"
        ),
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com"),
        recipient_list=[user.email],
        html_message=html_body or None,
    )
    return MagicLinkIssueResult(token=token, raw_token=raw_token, resume_url=resume_url)


def redeem_magic_link(
    raw_token: str,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> User | None:
    """Проверяет токен и помечает его использованным."""

    token = MagicLinkToken.objects.verify(raw_token)
    if token is None:
        return None
    token.mark_used(ip=ip, user_agent=user_agent)
    return token.user
