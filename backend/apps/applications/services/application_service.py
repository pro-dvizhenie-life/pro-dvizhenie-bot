"""Бизнес-логика управления заявками."""

from __future__ import annotations

from typing import Any, Dict, Optional

from config.constants import (
    APPLICATION_CONSENT_CODES,
    APPLICATION_CONTACT_EMAIL_CODES,
    APPLICATION_CONTACT_PHONE_CODES,
    APPLICATION_STATUS_ALLOWED_TRANSITIONS,
    DEFAULT_CONSENT_TYPE,
)
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from ..models import (
    Application,
    ApplicationComment,
    ApplicationStatusHistory,
    AuditLog,
    DataConsent,
)

CONSENT_DECLINED_MESSAGE = (
    "Спасибо, что заглянули! Без согласия на обработку персональных данных мы пока не можем принять заявку. "
    "Если решите продолжить, просто начните заполнение заново. Мы всегда на связи: 8 800 550 17 82 или в Telegram https://t.me/fond_prodvigenie."
)


def change_status(
    application: Application,
    new_status: str,
    changed_by: Optional[object] = None,
    *,
    request: Optional[HttpRequest] = None,
) -> Application:
    """Изменяет статус заявки с проверкой допустимых переходов."""

    allowed_transitions: dict[str, set[str]] = {
        source: set(targets)
        for source, targets in APPLICATION_STATUS_ALLOWED_TRANSITIONS.items()
    }

    current_status = application.status
    if current_status == new_status:
        return application

    if current_status not in allowed_transitions or new_status not in allowed_transitions.get(current_status, set()):
        raise ValidationError("Недопустимый переход статуса")

    with transaction.atomic():
        ApplicationStatusHistory.objects.create(
            application=application,
            old_status=current_status,
            new_status=new_status,
            changed_by=changed_by,
        )
        application.status = new_status
        if new_status == Application.Status.SUBMITTED:
            application.submitted_at = timezone.now()
        application.save(update_fields=["status", "submitted_at", "updated_at"])
        audit(
            action="status_change",
            table_name="applications",
            record_id=application.public_id,
            user=changed_by,
            request=request,
        )
    return application


def add_comment(
    application: Application,
    user: Optional[object],
    comment: str,
    *,
    is_urgent: bool = False,
    request: Optional[HttpRequest] = None,
) -> ApplicationComment:
    """Создаёт комментарий для заявки и пишет аудит."""

    with transaction.atomic():
        new_comment = ApplicationComment.objects.create(
            application=application,
            user=user,
            comment=comment,
            is_urgent=is_urgent,
        )
        audit(
            action="comment_add",
            table_name="comments",
            record_id=application.public_id,
            user=user,
            request=request,
        )
    return new_comment


def record_consent(
    *,
    user: object,
    application: Application,
    consent_type: str,
    is_given: bool,
    ip_address: Optional[str] = None,
) -> DataConsent:
    """Фиксирует согласие пользователя на обработку данных."""

    consent, _ = DataConsent.objects.update_or_create(
        user=user,
        application=application,
        consent_type=consent_type,
        defaults={
            "is_given": is_given,
            "given_at": timezone.now() if is_given else None,
            "ip_address": ip_address,
        },
    )
    return consent


def audit(
    *,
    action: str,
    table_name: str,
    record_id: Optional[str],
    user: Optional[object] = None,
    request: Optional[HttpRequest] = None,
) -> AuditLog:
    """Сохраняет запись аудита."""

    ip_address: Optional[str] = None
    if request is not None:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            ip_address = forwarded.split(",")[0].strip()
        else:
            ip_address = request.META.get("REMOTE_ADDR")
    log = AuditLog.objects.create(
        user=user if hasattr(user, "pk") else None,
        action=action,
        table_name=table_name,
        record_id=record_id,
        ip_address=ip_address,
    )
    return log


def _first_answer(answers: Dict[str, Any], codes: tuple[str, ...]) -> Optional[Any]:
    """Возвращает первый непустой ответ среди указанных кодов вопросов."""

    for code in codes:
        value = answers.get(code)
        if value not in (None, "", []):
            return value
    return None


def ensure_applicant_account(
    application: Application,
    answers: Dict[str, Any],
    *,
    request: Optional[HttpRequest] = None,
):
    """Обеспечивает создание/привязку пользователя к заявке по ответам анкеты."""

    email_value = _first_answer(answers, APPLICATION_CONTACT_EMAIL_CODES)
    phone_value = _first_answer(answers, APPLICATION_CONTACT_PHONE_CODES)
    if not email_value or not phone_value:
        return application.user

    email = str(email_value).strip().lower() if email_value else None
    phone = str(phone_value).strip() if phone_value else None
    if not email:
        # Без email идентифицировать пользователя надёжно нельзя
        return application.user
    User = get_user_model()

    user = application.user
    if user:
        # обновим email/phone при необходимости
        updates: list[str] = []
        if email and user.email != email and not User.objects.filter(email=email).exclude(pk=user.pk).exists():
            user.email = email
            updates.append("email")
        if phone and user.phone != phone and not User.objects.filter(phone=phone).exclude(pk=user.pk).exists():
            user.phone = phone
            updates.append("phone")
        if updates:
            user.save(update_fields=updates)
    else:
        # Пытаемся найти существующего пользователя
        user = User.objects.filter(email=email).first()
        if not user and phone:
            user = User.objects.filter(phone=phone).first()
        if user:
            updated: list[str] = []
            if user.email != email:
                user.email = email
                updated.append("email")
            if phone and user.phone != phone:
                user.phone = phone
                updated.append("phone")
            if updated:
                user.save(update_fields=updated)
        else:
            user = User.objects.create_user(email=email, phone=phone, password=None)

    if user and application.user_id != user.pk:
        application.user = user
        application.save(update_fields=["user", "updated_at"])

    if user and _first_answer(answers, APPLICATION_CONSENT_CODES) is True:
        existing = DataConsent.objects.filter(
            user=user,
            application=application,
            consent_type=DEFAULT_CONSENT_TYPE,
        ).first()
        if not existing or not existing.is_given:
            record_consent(
                user=user,
                application=application,
                consent_type=DEFAULT_CONSENT_TYPE,
                is_given=True,
                ip_address=None,
            )

    return user


def handle_consent_decline(application: Application) -> None:
    """Удаляет заявку и при необходимости связанную учётную запись."""

    user = application.user
    user_pk: Optional[int] = user.pk if user else None
    user_role = getattr(user, "role", None) if user else None
    other_applications = False
    if user:
        other_applications = user.applications.exclude(pk=application.pk).exists()

    with transaction.atomic():
        Application.objects.filter(pk=application.pk).delete()
        if user_pk is not None and not other_applications:
            user_model = get_user_model()
            applicant_role = getattr(user_model, "Role", None)
            if applicant_role is None or user_role == applicant_role.APPLICANT:
                user_model.objects.filter(pk=user_pk).delete()


__all__ = [
    "change_status",
    "add_comment",
    "record_consent",
    "ensure_applicant_account",
    "audit",
    "handle_consent_decline",
    "CONSENT_DECLINED_MESSAGE",
]
