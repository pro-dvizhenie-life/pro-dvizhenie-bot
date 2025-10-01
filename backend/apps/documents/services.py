"""Бизнес-логика работы с документами заявок."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from applications.models import Application, DocumentRequirement
from config.constants import (
    DOCUMENTS_DEFAULT_ALLOWED_CONTENT_TYPES,
    DOCUMENTS_DEFAULT_ALLOWED_EXTENSIONS,
    DOCUMENTS_DEFAULT_MAX_COUNT_PER_APPLICATION,
    DOCUMENTS_DEFAULT_MAX_FILE_SIZE,
)
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from .models import Document, DocumentEvent, DocumentVersion
from .storages import (
    AbstractDocumentStorage,
    DocumentStorageError,
    PresignedDownload,
    PresignedUpload,
)

_storage_instance: Optional[AbstractDocumentStorage] = None


@dataclass(slots=True)
class UploadBundle:
    document: Document
    version: DocumentVersion
    upload: PresignedUpload


def get_storage() -> AbstractDocumentStorage:
    """Возвращает синглтон экземпляр хранилища."""

    global _storage_instance
    if _storage_instance is not None:
        return _storage_instance
    config = getattr(settings, "DOCUMENTS_STORAGE", {})
    backend_path = config.get("BACKEND", "documents.storages.S3DocumentStorage")
    options = config.get("OPTIONS", {})
    backend_cls = import_string(backend_path)
    try:
        _storage_instance = backend_cls(**options)
    except TypeError as exc:  # pragma: no cover - ошибки конфигурации
        raise DocumentStorageError(f"Некорректные параметры DOCUMENTS_STORAGE. {exc}") from exc
    return _storage_instance


def _allowed_types() -> Sequence[str]:
    allowed = getattr(settings, "DOCUMENTS_ALLOWED_CONTENT_TYPES", None)
    if isinstance(allowed, (list, tuple, set)) and allowed:
        return tuple(str(item).strip() for item in allowed if str(item).strip())
    if isinstance(allowed, str) and allowed.strip():
        parts = [part.strip() for part in allowed.split(",") if part.strip()]
        if parts:
            return tuple(parts)
    return DOCUMENTS_DEFAULT_ALLOWED_CONTENT_TYPES


def _allowed_extensions() -> Sequence[str]:
    allowed = getattr(settings, "DOCUMENTS_ALLOWED_FILE_EXTENSIONS", None)
    if isinstance(allowed, (list, tuple, set)) and allowed:
        return tuple(str(item).strip().lower() for item in allowed if str(item).strip())
    if isinstance(allowed, str) and allowed.strip():
        parts = [part.strip().lower() for part in allowed.split(",") if part.strip()]
        if parts:
            return tuple(parts)
    return DOCUMENTS_DEFAULT_ALLOWED_EXTENSIONS


def _max_size() -> int:
    try:
        return int(
            getattr(settings, "DOCUMENTS_MAX_FILE_SIZE", DOCUMENTS_DEFAULT_MAX_FILE_SIZE)
        )
    except (TypeError, ValueError):  # pragma: no cover - защитный код
        return DOCUMENTS_DEFAULT_MAX_FILE_SIZE


def _max_documents_per_application() -> int:
    try:
        return int(
            getattr(
                settings,
                "DOCUMENTS_MAX_DOCUMENTS_PER_APPLICATION",
                DOCUMENTS_DEFAULT_MAX_COUNT_PER_APPLICATION,
            )
        )
    except (TypeError, ValueError):  # pragma: no cover - защитный код
        return DOCUMENTS_DEFAULT_MAX_COUNT_PER_APPLICATION


def _build_storage_key(application: Application, requirement: Optional[DocumentRequirement], filename: str) -> str:
    safe_name = Path(filename).name
    ext = Path(safe_name).suffix
    requirement_part = requirement.code if requirement else "misc"
    return f"applications/{application.public_id}/{requirement_part}/{uuid.uuid4()}{ext}"


def request_upload(
    *,
    application: Application,
    requirement: Optional[DocumentRequirement],
    document: Optional[Document],
    filename: str,
    content_type: str,
    size: int,
    user: Optional[object] = None,
) -> UploadBundle:
    """Создаёт новую попытку загрузки документа."""

    allowed_types = _allowed_types()
    if allowed_types and content_type not in allowed_types:
        raise ValidationError({"content_type": "Недопустимый MIME-тип файла."})
    extension = Path(filename).suffix.lstrip(".").lower()
    allowed_extensions = _allowed_extensions()
    if not extension or (allowed_extensions and extension not in allowed_extensions):
        raise ValidationError({"filename": "Недопустимое расширение файла."})
    max_size = _max_size()
    if size > max_size:
        raise ValidationError({"size": "Размер файла превышает допустимый лимит."})

    max_documents = _max_documents_per_application()

    with transaction.atomic():
        if document is None:
            active_documents_qs = Document.objects.filter(
                application=application,
                is_archived=False,
            ).select_for_update()
            if active_documents_qs.count() >= max_documents:
                raise ValidationError(
                    {
                        "documents": (
                            "Превышено допустимое количество документов для заявки. "
                            f"Допустимо не более {max_documents}."
                        )
                    }
                )
            document = Document.objects.create(
                application=application,
                requirement=requirement,
                code=requirement.code if requirement else "",
                title=requirement.label if requirement else "",
            )
            DocumentEvent.objects.create(
                document=document,
                event_type=DocumentEvent.EventType.CREATED,
                payload={"requirement": requirement.code if requirement else None},
            )
        last_version = (
            document.versions.select_for_update().order_by("-version").first()
        )
        next_version = 1 if last_version is None else last_version.version + 1
        storage_key = _build_storage_key(application, requirement, filename)
        version = DocumentVersion.objects.create(
            document=document,
            version=next_version,
            file_key=storage_key,
            original_name=filename,
            mime_type=content_type,
            size=size,
            uploaded_by=user if getattr(user, "is_authenticated", False) else None,
        )
        DocumentEvent.objects.create(
            document=document,
            version=version,
            event_type=DocumentEvent.EventType.UPLOAD_REQUESTED,
            payload={
                "version": next_version,
                "mime": content_type,
                "size": size,
            },
        )

    storage = get_storage()
    upload = storage.generate_upload(
        key=version.file_key,
        content_type=content_type,
        max_size=max_size,
    )
    return UploadBundle(document=document, version=version, upload=upload)


def complete_upload(
    version: DocumentVersion,
    *,
    checksum: Optional[str] = None,
    etag: Optional[str] = None,
    mark_available: bool = True,
) -> DocumentVersion:
    """Отмечает попытку загрузки завершённой."""

    with transaction.atomic():
        version.refresh_from_db()
        version.status = DocumentVersion.Status.UPLOADED
        version.uploaded_at = timezone.now()
        if checksum:
            version.checksum = checksum
        if etag:
            version.etag = etag
        version.save(update_fields=[
            "status",
            "uploaded_at",
            "checksum",
            "etag",
            "updated_at",
        ])
        DocumentEvent.objects.create(
            document=version.document,
            version=version,
            event_type=DocumentEvent.EventType.UPLOAD_COMPLETED,
            payload={"etag": etag, "checksum": checksum},
        )
    if mark_available:
        mark_version_available(version)
    return version


def mark_version_available(version: DocumentVersion) -> DocumentVersion:
    """Переводит версию в статус доступности (плейсхолдер вместо реальной AV-проверки)."""

    with transaction.atomic():
        version.refresh_from_db()
        version.status = DocumentVersion.Status.AVAILABLE
        version.antivirus_status = DocumentVersion.AntivirusStatus.SKIPPED
        version.ready_at = timezone.now()
        version.save(update_fields=["status", "antivirus_status", "ready_at", "updated_at"])
        Document.objects.filter(pk=version.document_id).update(
            current_version=version,
            updated_at=timezone.now(),
        )
        DocumentEvent.objects.create(
            document=version.document,
            version=version,
            event_type=DocumentEvent.EventType.STATUS_CHANGED,
            payload={"status": version.status},
        )
    return version


def list_versions(application: Application) -> Sequence[DocumentVersion]:
    """Возвращает список последних версий документов заявки."""

    return (
        DocumentVersion.objects.filter(document__application=application, document__is_archived=False)
        .select_related("document", "document__requirement")
        .order_by("document__created_at", "-version")
    )


def build_download(version: DocumentVersion) -> Optional[PresignedDownload]:
    """Формирует ссылку на скачивание для версии."""

    if version.status not in {
        DocumentVersion.Status.AVAILABLE,
        DocumentVersion.Status.UPLOADED,
    }:
        return None
    storage = get_storage()
    return storage.generate_download(key=version.file_key)


def archive_document(document: Document) -> None:
    """Помечает документ архивированным и удаляет объект из хранилища."""

    with transaction.atomic():
        document.refresh_from_db()
        document.is_archived = True
        document.save(update_fields=["is_archived", "updated_at"])
        DocumentEvent.objects.create(
            document=document,
            event_type=DocumentEvent.EventType.ARCHIVED,
            payload={},
        )
        keys = list(document.versions.values_list("file_key", flat=True))
    storage = get_storage()
    for key in keys:
        storage.delete_object(key=key)


__all__ = [
    "UploadBundle",
    "archive_document",
    "build_download",
    "complete_upload",
    "get_storage",
    "list_versions",
    "mark_version_available",
    "request_upload",
]
