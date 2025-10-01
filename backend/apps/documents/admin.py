"""Настройки административного интерфейса для документов."""

from __future__ import annotations

import json
from typing import List, Optional

from applications.admin import ApplicationAdmin, _answer_value  # type: ignore
from applications.models import Answer, Application, DocumentRequirement
from django import forms
from django.contrib import admin, messages
from django.contrib.admin.widgets import AutocompleteSelect
from django.core.exceptions import ValidationError
from django.db.models import Count, Prefetch
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import Document, DocumentEvent, DocumentVersion
from .services import build_documents_archive, build_download, ingest_admin_upload
from .storages import DocumentStorageError


class DocumentUploadAdminForm(forms.Form):
    """Форма загрузки документа из админки."""

    def __init__(
        self,
        *,
        admin_site,
        application_queryset,
        requirement_queryset,
        initial_application: Optional[Application] = None,
        data=None,
        files=None,
    ) -> None:
        super().__init__(data=data, files=files)
        application_field = Document._meta.get_field("application")
        requirement_field = Document._meta.get_field("requirement")

        self.fields["application"] = forms.ModelChoiceField(
            label="Заявка",
            queryset=application_queryset,
            widget=AutocompleteSelect(application_field, admin_site),
        )
        if initial_application:
            self.fields["application"].initial = initial_application.pk

        self.fields["requirement"] = forms.ModelChoiceField(
            label="Требование",
            queryset=requirement_queryset,
            required=False,
            widget=AutocompleteSelect(requirement_field, admin_site),
        )
        self.fields["title"] = forms.CharField(
            label="Название документа",
            max_length=200,
            required=False,
            widget=forms.TextInput(attrs={"class": "vTextField"}),
        )
        self.fields["notes"] = forms.CharField(
            label="Комментарий",
            required=False,
            widget=forms.Textarea(attrs={"rows": 3, "class": "vLargeTextField"}),
        )
        self.fields["document_file"] = forms.FileField(label="Файл")

        self.application_instance: Optional[Application] = initial_application

    def update_requirement_queryset(self, queryset) -> None:
        self.fields["requirement"].queryset = queryset

    def clean(self):
        cleaned = super().clean()
        application = cleaned.get("application")
        if application is not None:
            self.application_instance = application
        requirement = cleaned.get("requirement")
        if requirement and (application is None or requirement.survey_id != application.survey_id):
            self.add_error("requirement", "Требование не относится к выбранной заявке.")
        title = (cleaned.get("title") or "").strip()
        if requirement:
            cleaned["title"] = requirement.label
        elif not title:
            self.add_error("title", "Укажите название документа.")
        return cleaned



class DocumentStatusFilter(admin.SimpleListFilter):
    title = "Статус документа"
    parameter_name = "doc_status"

    def lookups(self, request, model_admin):
        return (
            ("missing", "Не загружен"),
            ("uploaded", "Загружен"),
            ("archived", "Архивирован"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "missing":
            return queryset.filter(current_version__isnull=True, is_archived=False)
        if value == "uploaded":
            return queryset.filter(current_version__isnull=False, is_archived=False)
        if value == "archived":
            return queryset.filter(is_archived=True)
        return queryset


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    answer_codes = {"q_fullname", "q_contact_name", "q_phone"}
    add_form_template = "admin/documents/document/add_form.html"
    list_display = (
        "application_link",
        "applicant_name",
        "requirement_label",
        "status_badge",
        "versions_count",
        "updated_at",
        "quick_actions",
    )
    list_display_links = ("application_link", "requirement_label")
    list_filter = (DocumentStatusFilter, "is_archived", "requirement")
    search_fields = (
        "public_id",
        "application__public_id",
        "requirement__label",
        "current_version__original_name",
    )
    readonly_fields = (
        "public_id",
        "created_at",
        "updated_at",
        "application_link",
        "applicant_name",
        "requirement_label",
        "status_badge",
        "versions_count",
        "download_link",
        "document_preview",
        "answers_summary",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "application",
                    "application_link",
                    "applicant_name",
                    "requirement",
                    "requirement_label",
                    "code",
                    "status_badge",
                    "versions_count",
                    "current_version",
                    "is_archived",
                    "title",
                    "notes",
                    "download_link",
                    "document_preview",
                )
            },
        ),
        (
            "Ответы анкеты",
            {
                "fields": ("answers_summary",),
                "classes": ("collapse",),
            },
        ),
        (
            "Служебная информация",
            {
                "fields": ("public_id", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
    actions = ("mark_archived", "mark_unarchived", "download_application_archive")
    autocomplete_fields = ("application", "requirement")
    upload_form_class = DocumentUploadAdminForm

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "application/<path:application_id>/export/",
                self.admin_site.admin_view(self.export_application_documents_view),
                name="documents_application_documents_export",
            )
        ]
        return custom + urls

    def add_view(self, request, form_url="", extra_context=None):
        extra_context = extra_context or {}
        application_qs = Application.objects.select_related("survey").order_by("-created_at")
        selected_application: Optional[Application] = None
        if request.method == "POST":
            app_id = request.POST.get("application")
        else:
            app_id = request.GET.get("application")
        if app_id:
            selected_application = application_qs.filter(pk=app_id).select_related("survey").first()

        requirement_qs = DocumentRequirement.objects.none()
        existing_documents: List[Document] = []
        if selected_application:
            requirement_qs = DocumentRequirement.objects.filter(survey=selected_application.survey).order_by("id")
            existing_documents = list(
                selected_application.documents.filter(is_archived=False)
                .select_related("requirement", "current_version")
                .order_by("requirement__id", "-updated_at")
            )

        form = self.upload_form_class(
            admin_site=self.admin_site,
            application_queryset=application_qs,
            requirement_queryset=requirement_qs,
            initial_application=selected_application,
            data=request.POST or None,
            files=request.FILES or None,
        )
        if request.method == "POST":
            # ensure requirement choices updated even if validation fails
            if form.application_instance:
                req_qs = DocumentRequirement.objects.filter(survey=form.application_instance.survey).order_by("id")
                form.update_requirement_queryset(req_qs)
            if form.is_valid():
                application = form.cleaned_data["application"]
                requirement = form.cleaned_data.get("requirement")
                title = form.cleaned_data.get("title")
                notes = form.cleaned_data.get("notes")
                uploaded_file = form.cleaned_data.get("document_file")
                try:
                    version = ingest_admin_upload(
                        application=application,
                        uploaded_file=uploaded_file,
                        user=request.user,
                        requirement=requirement,
                        title=title,
                        notes=notes,
                    )
                except ValidationError as exc:
                    form.add_error(None, exc)
                except DocumentStorageError as exc:
                    form.add_error("document_file", exc)
                else:
                    document = version.document
                    self.log_addition(request, document, "Initial upload")
                    return self.response_add(request, document)

        if form.application_instance and form.application_instance != selected_application:
            selected_application = form.application_instance
            existing_documents = list(
                selected_application.documents.filter(is_archived=False)
                .select_related("requirement", "current_version")
                .order_by("requirement__id", "-updated_at")
            )

        requirements_overview = self._build_requirements_overview(selected_application, existing_documents)
        documents_overview = self._build_existing_documents(existing_documents)

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "form": form,
            "selected_application": selected_application,
            "requirements_overview": requirements_overview,
            "documents_overview": documents_overview,
            "title": "Добавить документ",
        }
        media = form.media
        context["media"] = media
        context.update(extra_context)
        return TemplateResponse(request, self.add_form_template, context)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        answers_qs = Answer.objects.filter(question__code__in=self.answer_codes).select_related("question")
        queryset = queryset.select_related("application", "requirement", "current_version")
        queryset = queryset.annotate(versions_total=Count("versions", distinct=True))
        return queryset.prefetch_related(
            Prefetch("application__answers", queryset=answers_qs, to_attr="_prefetched_answers"),
            Prefetch("versions", queryset=DocumentVersion.objects.order_by("-created_at"), to_attr="_prefetched_versions"),
        )

    def application_link(self, obj):
        if not obj.application:
            return "—"
        url = reverse("admin:applications_application_change", args=[obj.application.pk])
        return format_html('<a href="{}">{}</a>', url, obj.application.public_id)

    application_link.short_description = "Заявка"

    def applicant_name(self, obj):
        if not obj.application:
            return "—"
        return ApplicationAdmin._display_text(_answer_value(obj.application, "q_fullname"))

    applicant_name.short_description = "ФИО подопечного"

    def requirement_label(self, obj):
        if obj.requirement:
            return obj.requirement.label
        return obj.title or obj.code or "Документ"

    requirement_label.short_description = "Документ"

    def status_badge(self, obj):
        if obj.is_archived:
            return format_html('<span style="padding:2px 8px;border-radius:999px;background:#6c757d;color:#fff;">Архив</span>')
        version = obj.current_version
        if not version:
            return format_html('<span style="padding:2px 8px;border-radius:999px;background:#dc3545;color:#fff;">Не загружен</span>')
        status_label = version.get_status_display()
        color_map = {
            DocumentVersion.Status.PENDING: "#fd7e14",
            DocumentVersion.Status.UPLOADED: "#0d6efd",
            DocumentVersion.Status.AVAILABLE: "#198754",
            DocumentVersion.Status.REJECTED: "#dc3545",
        }
        color = color_map.get(DocumentVersion.Status(version.status), "#0d6efd")
        return format_html(
            '<span style="padding:2px 8px;border-radius:999px;background:{};color:#fff;">{}</span>',
            color,
            status_label,
        )

    status_badge.short_description = "Статус"

    def versions_count(self, obj):
        return obj.versions_total

    versions_count.short_description = "Версий"

    def quick_actions(self, obj):
        if not obj.application:
            return "—"
        app_url = reverse("admin:applications_application_change", args=[obj.application.pk])
        versions_url = f"{reverse('admin:documents_documentversion_changelist')}?document__id__exact={obj.pk}"
        upload_url = f"{reverse('admin:documents_documentversion_add')}?document={obj.pk}"
        download = self._current_download(obj)
        archive_url = reverse("admin:documents_application_documents_export", args=[obj.application.pk])
        parts = [
            format_html('<a class="button" href="{}" target="_blank">Заявка</a>', app_url),
            format_html('<a class="button" href="{}">Архив заявки</a>', archive_url),
            format_html('<a class="button" href="{}" target="_blank">Версии</a>', versions_url),
            format_html('<a class="button" href="{}">Добавить версию</a>', upload_url),
        ]
        if download:
            parts.insert(2, format_html('<a class="button" href="{}" target="_blank" rel="noopener">Скачать</a>', download.url))
        return format_html(" ".join(str(item) for item in parts))

    quick_actions.short_description = "Быстрые действия"

    def _current_download(self, obj):
        version = obj.current_version
        if not version:
            return None
        try:
            return build_download(version)
        except DocumentStorageError:
            return None

    def download_link(self, obj):
        download = self._current_download(obj)
        if not download:
            return "—"
        name = obj.current_version.original_name if obj.current_version else "файл"
        return format_html('<a href="{}" target="_blank" rel="noopener">Скачать ({})</a>', download.url, name)

    download_link.short_description = "Скачать"

    def _document_status_tuple(self, document: Optional[Document]) -> tuple[str, str]:
        if not document:
            return "Не загружен", "status-missing"
        version = document.current_version
        if not version:
            return "Ожидает загрузки", "status-pending"
        try:
            status_enum = DocumentVersion.Status(version.status)
        except ValueError:
            status_enum = DocumentVersion.Status.PENDING
        label = version.get_status_display()
        status_class_map = {
            DocumentVersion.Status.AVAILABLE: "status-available",
            DocumentVersion.Status.UPLOADED: "status-uploaded",
            DocumentVersion.Status.PENDING: "status-pending",
            DocumentVersion.Status.REJECTED: "status-rejected",
        }
        return label, status_class_map.get(status_enum, "status-info")

    def _build_requirements_overview(
        self,
        application: Optional[Application],
        documents: List[Document],
    ) -> List[dict[str, object]]:
        if not application:
            return []
        docs_by_requirement = {doc.requirement_id: doc for doc in documents if doc.requirement_id}
        requirements = DocumentRequirement.objects.filter(survey=application.survey).order_by("id")
        overview: List[dict[str, object]] = []
        for requirement in requirements:
            document = docs_by_requirement.get(requirement.id)
            status_label, status_class = self._document_status_tuple(document)
            filename = document.current_version.original_name if document and document.current_version else ""
            overview.append(
                {
                    "label": requirement.label,
                    "status_label": status_label,
                    "status_class": status_class,
                    "filename": filename,
                }
            )
        return overview

    def _build_existing_documents(self, documents: List[Document]) -> List[dict[str, object]]:
        overview: List[dict[str, object]] = []
        for document in documents:
            if document.requirement_id:
                continue
            status_label, status_class = self._document_status_tuple(document)
            download = self._current_download(document)
            overview.append(
                {
                    "title": document.requirement.label if document.requirement else (document.title or document.code or "Документ"),
                    "status_label": status_label,
                    "status_class": status_class,
                    "filename": document.current_version.original_name if document.current_version else None,
                    "download_url": download.url if download else None,
                    "change_url": reverse("admin:documents_document_change", args=[document.pk]),
                }
            )
        return overview

    def document_preview(self, obj):
        download = self._current_download(obj)
        version = obj.current_version
        if not download or not version:
            return "—"
        mime = (version.mime_type or "").lower()
        if mime.startswith("image/"):
            return format_html(
                '<img src="{}" alt="{}" style="max-width:100%;max-height:400px;border:1px solid #d0d0d0;border-radius:4px;"/>',
                download.url,
                version.original_name or "Документ",
            )
        if mime == "application/pdf":
            return format_html(
                '<iframe src="{}" style="width:100%;height:600px;border:1px solid #d0d0d0;border-radius:4px;"></iframe>',
                download.url,
            )
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Открыть файл ({})</a>',
            download.url,
            version.original_name or mime or "файл",
        )

    document_preview.short_description = "Предпросмотр"

    def answers_summary(self, obj):
        application = obj.application
        if not application:
            return "—"
        answers = getattr(application, "_prefetched_answers", None)
        if answers is None:
            answers = list(application.answers.select_related("question__step"))
        if not answers:
            return "Ответов нет"
        sorted_answers = sorted(answers, key=ApplicationAdmin._answer_sort_key)
        rows = []
        current_step_id = object()
        for answer in sorted_answers:
            question = answer.question
            if not question:
                continue
            step = question.step
            step_id = step.id if step else None
            if step_id != current_step_id:
                title = step.title if step and step.title else (step.code if step else "Без шага")
                rows.append(
                    format_html(
                        '<tr class="answers-step"><th colspan="2" style="background:#f8f9fa;padding:8px 10px;">{}</th></tr>',
                        title,
                    )
                )
                current_step_id = step_id
            value_html = ApplicationAdmin._format_answer_value(answer.value)
            rows.append(
                format_html(
                    '<tr><th style="width:40%;vertical-align:top;padding:6px 10px;background:#fdfdfd;">{}</th>'
                    '<td style="padding:6px 10px;">{}</td></tr>',
                    question.label,
                    value_html,
                )
            )
        body = format_html("".join(str(row) for row in rows))
        return format_html(
            '<table class="admin-answers-table" style="width:100%;border-collapse:collapse;">{}</table>',
            body,
        )

    answers_summary.short_description = "Ответы анкеты"

    @admin.action(description="Перенести в архив")
    def mark_archived(self, request, queryset):
        updated = queryset.update(is_archived=True)
        self.message_user(request, f"Архивировано документов: {updated}")

    @admin.action(description="Вернуть из архива")
    def mark_unarchived(self, request, queryset):
        updated = queryset.update(is_archived=False)
        self.message_user(request, f"Снята отметка об архиве у {updated} документов")

    @admin.action(description="Скачать документы заявки архивом")
    def download_application_archive(self, request, queryset):
        application_ids = list(queryset.values_list("application_id", flat=True).distinct())
        if not application_ids:
            self.message_user(request, "Выберите хотя бы один документ", level=messages.WARNING)
            return None
        if len(application_ids) > 1:
            self.message_user(
                request,
                "Выберите документы только одной заявки для подготовки архива",
                level=messages.ERROR,
            )
            return None
        document = queryset.select_related("application").first()
        application = document.application if document else None
        if not application:
            self.message_user(request, "Не удалось определить заявку", level=messages.ERROR)
            return None
        documents_qs = Document.objects.filter(application=application, is_archived=False).select_related("current_version")
        label = f"application_{application.public_id}_{timezone.now():%Y%m%d_%H%M%S}_documents"
        archive = build_documents_archive(documents_qs, archive_label=label)
        if not archive:
            self.message_user(request, "У заявки нет доступных документов", level=messages.WARNING)
            return None
        response = HttpResponse(archive.content, content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{archive.filename}"'
        return response

    def export_application_documents_view(self, request, application_id):
        documents_qs = (
            Document.objects.filter(application_id=application_id, is_archived=False)
            .select_related("current_version", "application")
            .order_by("-created_at")
        )
        document = documents_qs.first()
        application = document.application if document else None
        if not application:
            self.message_user(request, "У заявки нет активных документов", level=messages.WARNING)
            return redirect(reverse("admin:documents_document_changelist"))
        list_url = f"{reverse('admin:documents_document_changelist')}?application__id__exact={application.pk}"
        label = f"application_{application.public_id}_{timezone.now():%Y%m%d_%H%M%S}_documents"
        archive = build_documents_archive(documents_qs, archive_label=label)
        if not archive:
            self.message_user(request, "Не удалось подготовить архив", level=messages.ERROR)
            return redirect(list_url)
        response = HttpResponse(archive.content, content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{archive.filename}"'
        return response


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = (
        "public_id",
        "document_link",
        "applicant_name",
        "requirement_label",
        "status_badge",
        "is_current",
        "uploaded_at",
        "uploaded_by_display",
        "size_readable",
        "actions_column",
        "notes_short",
    )
    list_filter = (
        "status",
        "document__requirement",
        "uploaded_at",
        "document__is_archived",
        "uploaded_by",
    )
    search_fields = (
        "public_id",
        "document__public_id",
        "document__application__public_id",
        "document__requirement__label",
        "original_name",
        "mime_type",
        "file_key",
    )
    readonly_fields = (
        "public_id",
        "created_at",
        "updated_at",
        "uploaded_at",
        "ready_at",
        "status_badge",
        "size_readable",
        "download_link",
        "document_preview",
    )
    actions = ("mark_as_current", "archive_version")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        answers_qs = Answer.objects.filter(question__code__in=DocumentAdmin.answer_codes).select_related("question")
        return queryset.select_related("document", "document__application", "document__requirement", "uploaded_by").prefetch_related(
            Prefetch("document__application__answers", queryset=answers_qs, to_attr="_prefetched_answers"),
        )

    def document_link(self, obj):
        url = reverse("admin:documents_document_change", args=[obj.document.pk])
        label = obj.document.requirement.label if obj.document.requirement else obj.document.code or obj.document.public_id
        return format_html('<a href="{}">{}</a>', url, label)

    document_link.short_description = "Документ"

    def applicant_name(self, obj):
        application = obj.document.application
        return ApplicationAdmin._display_text(_answer_value(application, "q_fullname")) if application else "—"

    applicant_name.short_description = "ФИО подопечного"

    def requirement_label(self, obj):
        requirement = obj.document.requirement
        return requirement.label if requirement else obj.document.title or obj.document.code or "Документ"

    requirement_label.short_description = "Требование"

    def status_badge(self, obj):
        label = obj.get_status_display()
        color_map = {
            DocumentVersion.Status.PENDING: "#fd7e14",
            DocumentVersion.Status.UPLOADED: "#0d6efd",
            DocumentVersion.Status.AVAILABLE: "#198754",
            DocumentVersion.Status.REJECTED: "#dc3545",
        }
        color = color_map.get(DocumentVersion.Status(obj.status), "#6c757d")
        return format_html(
            '<span style="padding:2px 8px;border-radius:999px;background:{};color:#fff;">{}</span>',
            color,
            label,
        )

    status_badge.short_description = "Статус"

    def is_current(self, obj):
        return obj.document.current_version_id == obj.id

    is_current.boolean = True
    is_current.short_description = "Текущая"

    def uploaded_by_display(self, obj):
        if obj.uploaded_by:
            email = (obj.uploaded_by.email or "").strip()
            phone = (obj.uploaded_by.phone or "").strip()
            if email and phone:
                return f"{email} / {phone}"
            return email or phone or str(obj.uploaded_by)
        return "Пользователь"

    uploaded_by_display.short_description = "Загрузил"

    def size_readable(self, obj):
        size = obj.size or 0
        units = ["Б", "КБ", "МБ", "ГБ"]
        idx = 0
        size_float = float(size)
        while size_float >= 1024 and idx < len(units) - 1:
            size_float /= 1024
            idx += 1
        return f"{size_float:.1f} {units[idx]}"

    size_readable.short_description = "Размер"

    def actions_column(self, obj):
        change_url = reverse("admin:documents_documentversion_change", args=[obj.pk])
        download = None
        try:
            download = build_download(obj)
        except DocumentStorageError:
            download = None
        parts = [format_html('<a class="button" href="{}">Открыть</a>', change_url)]
        if download:
            parts.insert(0, format_html('<a class="button" href="{}" target="_blank" rel="noopener">Скачать</a>', download.url))
        return format_html(" ".join(str(item) for item in parts))

    actions_column.short_description = "Действия"

    def notes_short(self, obj):
        notes = obj.document.notes or ""
        if not notes:
            return "—"
        return notes if len(notes) <= 40 else f"{notes[:37]}…"

    notes_short.short_description = "Комментарий"

    def download_link(self, obj):
        try:
            download = build_download(obj)
        except DocumentStorageError:
            download = None
        if not download:
            return "—"
        return format_html('<a href="{}" target="_blank" rel="noopener">Скачать ({})</a>', download.url, obj.original_name)

    download_link.short_description = "Скачать"

    def document_preview(self, obj):
        try:
            download = build_download(obj)
        except DocumentStorageError:
            download = None
        if not download:
            return "—"
        mime = (obj.mime_type or "").lower()
        if mime.startswith("image/"):
            return format_html(
                '<img src="{}" alt="{}" style="max-width:100%;max-height:400px;border:1px solid #d0d0d0;border-radius:4px;"/>',
                download.url,
                obj.original_name or "Документ",
            )
        if mime == "application/pdf":
            return format_html(
                '<iframe src="{}" style="width:100%;height:600px;border:1px solid #d0d0d0;border-radius:4px;"></iframe>',
                download.url,
            )
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Открыть файл ({})</a>',
            download.url,
            obj.original_name or mime or "файл",
        )

    document_preview.short_description = "Предпросмотр"

    @admin.action(description="Сделать текущей версией")
    def mark_as_current(self, request, queryset):
        updated = 0
        for version in queryset.select_related("document"):
            version.document.current_version = version
            version.document.save(update_fields=["current_version", "updated_at"])
            updated += 1
        self.message_user(request, f"Назначено текущих версий: {updated}")

    @admin.action(description="Архивировать документ")
    def archive_version(self, request, queryset):
        doc_ids = queryset.values_list("document_id", flat=True)
        Document.objects.filter(id__in=doc_ids).update(is_archived=True)
        self.message_user(request, "Документы перенесены в архив")


@admin.register(DocumentEvent)
class DocumentEventAdmin(admin.ModelAdmin):
    event_labels = {
        DocumentEvent.EventType.CREATED: "Создан документ",
        DocumentEvent.EventType.UPLOAD_REQUESTED: "Запрошена загрузка",
        DocumentEvent.EventType.UPLOAD_COMPLETED: "Загрузка завершена",
        DocumentEvent.EventType.STATUS_CHANGED: "Статус изменён",
        DocumentEvent.EventType.ARCHIVED: "Архивирование",
    }
    list_display = (
        "created_at",
        "document_link",
        "applicant_name",
        "version_link",
        "event_label",
        "payload_summary",
        "user_display",
    )
    list_filter = ("event_type", "created_at", "document__requirement")
    search_fields = (
        "document__public_id",
        "document__application__public_id",
        "version__public_id",
        "payload",
    )
    readonly_fields = ("created_at", "document_link", "event_label", "payload_pretty", "user_display")
    ordering = ("-created_at", "-id")
    date_hierarchy = "created_at"

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        answers_qs = Answer.objects.filter(question__code__in=DocumentAdmin.answer_codes).select_related("question")
        return queryset.select_related(
            "document",
            "document__application",
            "document__application__survey",
            "version",
        ).prefetch_related(
            Prefetch("document__application__answers", queryset=answers_qs, to_attr="_prefetched_answers"),
        )

    def document_link(self, obj):
        url = reverse("admin:documents_document_change", args=[obj.document.pk])
        label = obj.document.requirement.label if obj.document.requirement else obj.document.code or obj.document.public_id
        return format_html('<a href="{}">{}</a>', url, label)

    document_link.short_description = "Документ"

    def version_link(self, obj):
        if not obj.version:
            return "—"
        url = reverse("admin:documents_documentversion_change", args=[obj.version.pk])
        return format_html('<a href="{}">Версия v{}</a>', url, obj.version.version)

    version_link.short_description = "Версия"

    def applicant_name(self, obj):
        application = obj.document.application
        return ApplicationAdmin._display_text(_answer_value(application, "q_fullname")) if application else "—"

    applicant_name.short_description = "ФИО подопечного"

    def event_label(self, obj):
        return self.event_labels.get(obj.event_type, obj.get_event_type_display())

    event_label.short_description = "Событие"

    def payload_summary(self, obj):
        payload = obj.payload or {}
        if not payload:
            return "—"
        parts = []
        size = payload.get("size")
        if size:
            parts.append(f"Размер: {int(size) / 1024:.1f} КБ")
        mime = payload.get("mime") or payload.get("mime_type")
        if mime:
            parts.append(f"Формат: {mime}")
        status = payload.get("status") or payload.get("new_status")
        if status:
            parts.append(f"Статус: {status}")
        reason = payload.get("reason") or payload.get("comment")
        if reason:
            parts.append(f"Комментарий: {reason}")
        if not parts:
            parts = [str(payload)]
        return "; ".join(parts)

    payload_summary.short_description = "Детали"

    def payload_pretty(self, obj):
        payload = obj.payload or {}
        if not payload:
            return "—"
        formatted = json.dumps(payload, ensure_ascii=False, indent=2)
        return format_html('<pre style="white-space: pre-wrap; margin: 0;">{}</pre>', formatted)

    payload_pretty.short_description = "Payload"

    def user_display(self, obj):
        version = obj.version
        if version and version.uploaded_by:
            email = (version.uploaded_by.email or "").strip()
            phone = (version.uploaded_by.phone or "").strip()
            if email and phone:
                return f"{email} / {phone}"
            return email or phone or str(version.uploaded_by)
        return "Система"

    user_display.short_description = "Инициатор"

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj:
            if "document_link" not in readonly:
                readonly.append("document_link")
            if "event_label" not in readonly:
                readonly.append("event_label")
            if "payload_pretty" not in readonly:
                readonly.append("payload_pretty")
            if "user_display" not in readonly:
                readonly.append("user_display")
        return readonly

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj)) or [(None, {"fields": ()})]
        base_fields = (
            "document",
            "document_link",
            "version",
            "event_type",
            "event_label",
            "payload",
            "payload_pretty",
            "user_display",
            "created_at",
        )
        fieldsets[0] = (fieldsets[0][0], {"fields": base_fields})
        return fieldsets
