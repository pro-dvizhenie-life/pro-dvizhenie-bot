"""Бизнес-логика работы с документами заявок."""

from __future__ import annotations

import hashlib
import mimetypes
import re
import uuid
from collections import Counter
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Iterable, Optional, Sequence
from zipfile import ZIP_DEFLATED, ZipFile

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


@dataclass(slots=True)
class DocumentBinary:
    filename: str
    content: bytes
    mime_type: str


@dataclass(slots=True)
class DocumentArchive:
    filename: str
    content: bytes


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
    """Возвращает допустимые MIME-типы загрузок из настроек или дефолта."""

    allowed = getattr(settings, "DOCUMENTS_ALLOWED_CONTENT_TYPES", None)
    if isinstance(allowed, (list, tuple, set)) and allowed:
        return tuple(str(item).strip() for item in allowed if str(item).strip())
    if isinstance(allowed, str) and allowed.strip():
        parts = [part.strip() for part in allowed.split(",") if part.strip()]
        if parts:
            return tuple(parts)
    return DOCUMENTS_DEFAULT_ALLOWED_CONTENT_TYPES


def _allowed_extensions() -> Sequence[str]:
    """Возвращает разрешённые расширения файлов."""

    allowed = getattr(settings, "DOCUMENTS_ALLOWED_FILE_EXTENSIONS", None)
    if isinstance(allowed, (list, tuple, set)) and allowed:
        return tuple(str(item).strip().lower() for item in allowed if str(item).strip())
    if isinstance(allowed, str) and allowed.strip():
        parts = [part.strip().lower() for part in allowed.split(",") if part.strip()]
        if parts:
            return tuple(parts)
    return DOCUMENTS_DEFAULT_ALLOWED_EXTENSIONS


def _max_size() -> int:
    """Определяет максимальный размер файла для загрузки."""

    try:
        return int(
            getattr(settings, "DOCUMENTS_MAX_FILE_SIZE", DOCUMENTS_DEFAULT_MAX_FILE_SIZE)
        )
    except (TypeError, ValueError):  # pragma: no cover - защитный код
        return DOCUMENTS_DEFAULT_MAX_FILE_SIZE


def _max_documents_per_application() -> int:
    """Возвращает лимит активных документов для одной заявки."""

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
    """Формирует уникальный ключ объекта в хранилище для версии документа."""

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


def fetch_document_binary(version: DocumentVersion) -> Optional[DocumentBinary]:
    """Загружает бинарное содержимое текущей версии документа."""

    if version.status not in {
        DocumentVersion.Status.AVAILABLE,
        DocumentVersion.Status.UPLOADED,
    }:
        return None
    storage = get_storage()
    try:
        content = storage.read_object(key=version.file_key)
    except DocumentStorageError:
        return None

    filename = version.original_name or f"document-{version.document_id}.bin"
    return DocumentBinary(filename=filename, content=content, mime_type=version.mime_type)


def _sanitize_filename(name: str) -> str:
    """Удаляет недопустимые символы из имени файла для архива."""

    cleaned = name.strip() or "document"
    cleaned = re.sub(r"[\\/:*?\"<>|]", "_", cleaned)
    return cleaned


def build_documents_archive(
    documents: Iterable[Document],
    *,
    archive_label: str,
) -> Optional[DocumentArchive]:
    """Формирует zip-архив с последними версиями выбранных документов."""

    buffer = BytesIO()
    existing_names: Counter[str] = Counter()
    added = 0

    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as zip_file:
        for document in documents:
            version = document.current_version
            if not version:
                continue
            binary = fetch_document_binary(version)
            if not binary:
                continue
            title = binary.filename or "document"
            base = _sanitize_filename(Path(title).stem)
            ext = Path(title).suffix or ".bin"
            counter = existing_names[base]
            existing_names[base] += 1
            if counter:
                archive_name = f"{base}_{counter}{ext}"
            else:
                archive_name = f"{base}{ext}"
            zip_file.writestr(archive_name, binary.content)
            added += 1

    if added == 0:
        return None

    safe_label = _sanitize_filename(archive_label)
    filename = f"{safe_label}.zip"
    buffer.seek(0)
    return DocumentArchive(filename=filename, content=buffer.read())


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


def ingest_admin_upload(
    *,
    application: Application,
    uploaded_file,
    user: Optional[object] = None,
    requirement: Optional[DocumentRequirement] = None,
    document: Optional[Document] = None,
    title: Optional[str] = None,
    notes: Optional[str] = None,
) -> DocumentVersion:
    """Сохраняет файл, загруженный из админки, и помечает версию доступной."""

    filename = getattr(uploaded_file, "name", None) or "document"
    content_type = getattr(uploaded_file, "content_type", None) or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    file_bytes = uploaded_file.read()
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    size = getattr(uploaded_file, "size", None) or len(file_bytes)

    existing_document = document
    bundle = request_upload(
        application=application,
        requirement=requirement,
        document=document,
        filename=filename,
        content_type=content_type,
        size=size,
        user=user,
    )
    document_created = existing_document is None
    document_instance = bundle.document

    storage = get_storage()
    try:
        storage.upload_bytes(key=bundle.version.file_key, content=file_bytes, content_type=content_type)
    except Exception as exc:  # pragma: no cover - зависит от инфраструктуры
        bundle.version.delete()
        if document_created:
            document_instance.delete()
        raise DocumentStorageError("Не удалось загрузить документ в хранилище") from exc

    checksum = hashlib.md5(file_bytes).hexdigest() if file_bytes else None
    complete_upload(bundle.version, checksum=checksum)

    update_fields: set[str] = set()
    if notes is not None and notes != (document_instance.notes or ""):
        document_instance.notes = notes
        update_fields.add("notes")
    effective_title = title or (requirement.label if requirement else document_instance.title)
    if effective_title and effective_title != (document_instance.title or ""):
        document_instance.title = effective_title
        update_fields.add("title")
    if update_fields:
        document_instance.save(update_fields=[*update_fields, "updated_at"])

    bundle.version.refresh_from_db()
    return bundle.version


__all__ = [
    "UploadBundle",
    "archive_document",
    "build_documents_archive",
    "build_download",
    "complete_upload",
    "fetch_document_binary",
    "get_storage",
    "list_versions",
    "mark_version_available",
    "request_upload",
    "ingest_admin_upload",
]
