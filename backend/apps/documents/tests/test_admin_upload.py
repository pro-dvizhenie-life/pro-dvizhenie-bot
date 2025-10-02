"""Тесты загрузки документов через административный сервис."""

from __future__ import annotations

from unittest.mock import patch

from applications.models import Application, DocumentRequirement, Survey
from django.contrib.admin.sites import AdminSite
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from documents.admin import DocumentUploadAdminForm
from documents.models import DocumentVersion
from documents.services import PresignedUpload, ingest_admin_upload


class DummyStorage:
    """Простое хранилище для тестов."""

    def __init__(self):
        self.uploaded = []

    def generate_upload(self, *, key: str, content_type: str, max_size: int):
        return PresignedUpload(url="", method="POST", fields={}, headers={})

    def upload_bytes(self, *, key: str, content: bytes, content_type: str) -> None:
        self.uploaded.append((key, len(content), content_type))

    def generate_download(self, *, key: str, expires_in=None):  # pragma: no cover - не используется
        raise NotImplementedError

    def delete_object(self, *, key: str) -> None:  # pragma: no cover - не используется
        raise NotImplementedError

    def read_object(self, *, key: str) -> bytes:  # pragma: no cover - не используется
        raise NotImplementedError


class AdminDocumentUploadTests(TestCase):
    def setUp(self) -> None:
        self.survey = Survey.objects.create(code="admin-test", title="Admin Test")
        self.requirement = DocumentRequirement.objects.create(
            survey=self.survey,
            code="passport",
            label="Паспорт",
        )
        self.application = Application.objects.create(survey=self.survey)
        self.storage = DummyStorage()
        self.admin_site = AdminSite()

    def test_ingest_admin_upload_creates_document_and_version(self):
        uploaded = SimpleUploadedFile("test.pdf", b"pdf-bytes", content_type="application/pdf")
        with patch("documents.services.get_storage", return_value=self.storage):
            version = ingest_admin_upload(
                application=self.application,
                uploaded_file=uploaded,
                user=None,
                requirement=self.requirement,
                title=None,
            )
        self.assertIsInstance(version, DocumentVersion)
        self.assertEqual(version.document.application, self.application)
        self.assertEqual(version.document.requirement, self.requirement)
        self.assertEqual(version.status, DocumentVersion.Status.AVAILABLE)
        self.assertEqual(version.document.current_version, version)
        self.assertTrue(self.storage.uploaded)

    def test_upload_form_rejects_requirement_from_other_survey(self):
        other_survey = Survey.objects.create(code="other", title="Other")
        other_requirement = DocumentRequirement.objects.create(survey=other_survey, code="other", label="Other")
        form = DocumentUploadAdminForm(
            admin_site=self.admin_site,
            application_queryset=Application.objects.all(),
            requirement_queryset=DocumentRequirement.objects.all(),
            data={
                "application": self.application.pk,
                "requirement": other_requirement.pk,
                "title": "",
            },
            files={"document_file": SimpleUploadedFile("x.pdf", b"data", content_type="application/pdf")},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("Требование не относится", form.errors["requirement"][0])

    def test_upload_form_autofills_title_from_requirement(self):
        requirement = DocumentRequirement.objects.create(survey=self.survey, code="passport", label="Паспорт")
        form = DocumentUploadAdminForm(
            admin_site=self.admin_site,
            application_queryset=Application.objects.all(),
            requirement_queryset=DocumentRequirement.objects.filter(pk=requirement.pk),
            data={
                "application": self.application.pk,
                "requirement": requirement.pk,
                "title": "",
            },
            files={"document_file": SimpleUploadedFile("x.pdf", b"data", content_type="application/pdf")},
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["title"], "Паспорт")
