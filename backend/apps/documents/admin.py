"""Настройки административного интерфейса для документов."""

from django.contrib import admin

from .models import Document, DocumentEvent, DocumentVersion


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "public_id",
        "application",
        "code",
        "requirement",
        "is_archived",
        "created_at",
    )
    list_filter = ("is_archived", "requirement")
    search_fields = ("public_id", "application__public_id", "code", "title")
    readonly_fields = ("created_at", "updated_at", "public_id", "current_version")


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = (
        "public_id",
        "document",
        "version",
        "status",
        "antivirus_status",
        "uploaded_at",
        "size",
    )
    list_filter = ("status", "antivirus_status")
    search_fields = ("public_id", "document__public_id", "original_name", "file_key")
    readonly_fields = (
        "public_id",
        "created_at",
        "updated_at",
        "uploaded_at",
        "ready_at",
    )


@admin.register(DocumentEvent)
class DocumentEventAdmin(admin.ModelAdmin):
    list_display = ("document", "version", "event_type", "created_at")
    list_filter = ("event_type",)
    search_fields = ("document__public_id", "version__public_id")
    readonly_fields = ("created_at",)
