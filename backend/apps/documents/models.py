"""Модели домена документов заявок."""

from __future__ import annotations

import uuid

from applications.models import Application, DocumentRequirement
from config.constants import (
    DOCUMENT_CODE_MAX_LENGTH,
    DOCUMENT_EVENT_TYPE_MAX_LENGTH,
    DOCUMENT_TITLE_MAX_LENGTH,
    DOCUMENT_VERSION_CHECKSUM_MAX_LENGTH,
    DOCUMENT_VERSION_ETAG_MAX_LENGTH,
    DOCUMENT_VERSION_FILE_KEY_MAX_LENGTH,
    DOCUMENT_VERSION_MIME_TYPE_MAX_LENGTH,
    DOCUMENT_VERSION_ORIGINAL_NAME_MAX_LENGTH,
    DOCUMENT_VERSION_STATUS_MAX_LENGTH,
)
from django.conf import settings
from django.db import models


class Document(models.Model):
    """Документ, загруженный в рамках заявки."""

    public_id = models.UUIDField(
        "Публичный идентификатор",
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    application = models.ForeignKey(
        Application,
        verbose_name="Заявка",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    requirement = models.ForeignKey(
        DocumentRequirement,
        verbose_name="Требование",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    code = models.SlugField(
        "Код документа",
        max_length=DOCUMENT_CODE_MAX_LENGTH,
        blank=True,
        help_text="Служебный код (обычно совпадает с требованием).",
    )
    title = models.CharField(
        "Название",
        max_length=DOCUMENT_TITLE_MAX_LENGTH,
        blank=True,
        help_text="Отображаемое имя документа.",
    )
    notes = models.TextField("Комментарий", blank=True)
    current_version = models.ForeignKey(
        "DocumentVersion",
        verbose_name="Текущая версия",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="current_for_documents",
    )
    is_archived = models.BooleanField("Архивирован", default=False)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        verbose_name = "Документ"
        verbose_name_plural = "Документы"
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:  # pragma: no cover - строковое представление
        return f"{self.application.public_id}:{self.code or self.public_id}"


class DocumentVersion(models.Model):
    """Конкретная версия файла документа."""

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает загрузки"
        UPLOADED = "uploaded", "Загружен"
        AVAILABLE = "available", "Готов к использованию"
        REJECTED = "rejected", "Отклонён"

    class AntivirusStatus(models.TextChoices):
        PENDING = "pending", "Ожидает проверки"
        CLEAN = "clean", "Проверен"
        INFECTED = "infected", "Выявлено заражение"
        FAILED = "failed", "Ошибка проверки"
        SKIPPED = "skipped", "Проверка не выполнялась"

    public_id = models.UUIDField(
        "Публичный идентификатор версии",
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    document = models.ForeignKey(
        Document,
        verbose_name="Документ",
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version = models.PositiveIntegerField("Номер версии", default=1)
    file_key = models.CharField("Ключ в хранилище", max_length=DOCUMENT_VERSION_FILE_KEY_MAX_LENGTH)
    original_name = models.CharField(
        "Исходное имя файла",
        max_length=DOCUMENT_VERSION_ORIGINAL_NAME_MAX_LENGTH,
    )
    mime_type = models.CharField("MIME-тип", max_length=DOCUMENT_VERSION_MIME_TYPE_MAX_LENGTH)
    size = models.BigIntegerField("Размер файла")
    checksum = models.CharField(
        "Контрольная сумма",
        max_length=DOCUMENT_VERSION_CHECKSUM_MAX_LENGTH,
        blank=True,
    )
    etag = models.CharField("ETag", max_length=DOCUMENT_VERSION_ETAG_MAX_LENGTH, blank=True)
    status = models.CharField(
        "Статус",
        max_length=DOCUMENT_VERSION_STATUS_MAX_LENGTH,
        choices=Status.choices,
        default=Status.PENDING,
    )
    antivirus_status = models.CharField(
        "Статус антивирусной проверки",
        max_length=DOCUMENT_VERSION_STATUS_MAX_LENGTH,
        choices=AntivirusStatus.choices,
        default=AntivirusStatus.PENDING,
    )
    antivirus_message = models.CharField("Комментарий проверки", max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Загружен пользователем",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    uploaded_at = models.DateTimeField("Время загрузки", null=True, blank=True)
    ready_at = models.DateTimeField("Готово к использованию", null=True, blank=True)
    extra = models.JSONField("Доп. сведения", default=dict, blank=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "Версия документа"
        verbose_name_plural = "Версии документов"
        ordering = ("-created_at", "-id")
        unique_together = (("document", "version"),)

    def __str__(self) -> str:  # pragma: no cover - строковое представление
        return f"{self.document.public_id}:v{self.version}"


class DocumentEvent(models.Model):
    """Журнал событий по документам."""

    class EventType(models.TextChoices):
        CREATED = "created", "Создан"
        UPLOAD_REQUESTED = "upload_requested", "Запрошена загрузка"
        UPLOAD_COMPLETED = "upload_completed", "Загрузка завершена"
        STATUS_CHANGED = "status_changed", "Изменение статуса"
        ARCHIVED = "archived", "Документ архивирован"

    document = models.ForeignKey(
        Document,
        verbose_name="Документ",
        on_delete=models.CASCADE,
        related_name="events",
    )
    version = models.ForeignKey(
        DocumentVersion,
        verbose_name="Версия",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="events",
    )
    event_type = models.CharField(
        "Тип события",
        max_length=DOCUMENT_EVENT_TYPE_MAX_LENGTH,
        choices=EventType.choices,
    )
    payload = models.JSONField("Данные", default=dict, blank=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Событие документа"
        verbose_name_plural = "События документа"
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:  # pragma: no cover - строковое представление
        return f"{self.document.public_id}:{self.event_type}"


__all__ = ["Document", "DocumentVersion", "DocumentEvent"]
