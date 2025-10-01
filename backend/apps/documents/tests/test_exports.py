"""Проверки архивации документов."""

from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

from applications.models import Application, Question, Step, Survey
from django.test import TestCase

from ..models import Document, DocumentRequirement, DocumentVersion
from ..services import build_documents_archive, fetch_document_binary


class _DummyStorage:
    def __init__(self, content_map):
        self._content_map = content_map

    def read_object(self, *, key: str) -> bytes:  # type: ignore[override]
        return self._content_map[key]


class DocumentArchiveTests(TestCase):
    """Тесты формирования архивов документов."""

    def setUp(self):
        self.survey = Survey.objects.create(code="survey", title="Survey", version="1", is_active=True)
        self.step = Step.objects.create(survey=self.survey, code="step", title="Step", order=1)
        Question.objects.create(step=self.step, code="q_fullname", label="ФИО", type="text", required=True)
        self.requirement = DocumentRequirement.objects.create(survey=self.survey, code="req1", label="Документ")
        self.application = Application.objects.create(survey=self.survey, status=Application.Status.SUBMITTED)

    def _create_document(self, key: str, name: str) -> Document:
        document = Document.objects.create(
            application=self.application,
            requirement=self.requirement,
            code="code",
            title="title",
        )
        version = DocumentVersion.objects.create(
            document=document,
            version=1,
            file_key=key,
            original_name=name,
            mime_type="application/pdf",
            size=10,
            status=DocumentVersion.Status.AVAILABLE,
        )
        document.current_version = version
        document.save(update_fields=["current_version"])
        return document

    def test_fetch_document_binary_reads_storage(self):
        document = self._create_document("key1", "file.pdf")
        from unittest.mock import patch

        storage = _DummyStorage({"key1": b"file-content"})
        with patch("documents.services.get_storage", return_value=storage):
            binary = fetch_document_binary(document.current_version)
        self.assertIsNotNone(binary)
        self.assertEqual(binary.content, b"file-content")
        self.assertEqual(binary.filename, "file.pdf")

    def test_build_documents_archive_zips_files(self):
        doc1 = self._create_document("key1", "file.pdf")
        doc2 = self._create_document("key2", "file.pdf")
        from unittest.mock import patch

        storage = _DummyStorage({"key1": b"first", "key2": b"second"})
        with patch("documents.services.get_storage", return_value=storage):
            archive = build_documents_archive([doc1, doc2], archive_label="archive_test")
        self.assertIsNotNone(archive)
        with BytesIO(archive.content) as buffer:
            with ZipFile(buffer) as zip_file:
                names = sorted(zip_file.namelist())
                self.assertEqual(len(names), 2)
                self.assertNotEqual(names[0], names[1])
                contents = sorted(zip_file.read(name) for name in names)
                self.assertEqual(contents, [b"first", b"second"])
