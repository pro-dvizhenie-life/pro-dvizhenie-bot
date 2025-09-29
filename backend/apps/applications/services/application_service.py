"""Бизнес-логика управления заявками."""

from __future__ import annotations

from typing import Optional

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


def change_status(
    application: Application,
    new_status: str,
    changed_by: Optional[object] = None,
    *,
    request: Optional[HttpRequest] = None,
) -> Application:
    """Изменяет статус заявки с проверкой допустимых переходов."""

    allowed_transitions: dict[str, set[str]] = {
        Application.Status.DRAFT: {Application.Status.SUBMITTED},
        Application.Status.SUBMITTED: {
            Application.Status.UNDER_REVIEW,
            Application.Status.APPROVED,
            Application.Status.REJECTED,
        },
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


__all__ = [
    "change_status",
    "add_comment",
    "record_consent",
    "audit",
]
