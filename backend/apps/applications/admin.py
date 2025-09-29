"""Регистрация моделей приложения заявок в админке."""

from django.contrib import admin

from .models import (
    Application,
    ApplicationComment,
    ApplicationStatusHistory,
    AuditLog,
    DataConsent,
    Option,
    Question,
    Step,
    Survey,
)


class OptionInline(admin.TabularInline):
    model = Option
    extra = 0


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "version", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "title")


@admin.register(Step)
class StepAdmin(admin.ModelAdmin):
    list_display = ("code", "survey", "order")
    list_filter = ("survey",)
    search_fields = ("code", "title", "survey__code")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("code", "step", "type", "required")
    list_filter = ("type", "required", "step__survey")
    search_fields = ("code", "label", "step__code")
    inlines = [OptionInline]


class CommentInline(admin.TabularInline):
    model = ApplicationComment
    extra = 0
    can_delete = False
    readonly_fields = ("user", "comment", "is_urgent", "created_at")


class StatusInline(admin.TabularInline):
    model = ApplicationStatusHistory
    extra = 0
    can_delete = False
    readonly_fields = ("old_status", "new_status", "changed_by", "created_at")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "public_id",
        "survey",
        "status",
        "applicant_type",
        "current_stage",
        "created_at",
        "submitted_at",
    )
    list_filter = ("status", "survey")
    search_fields = ("public_id",)
    inlines = [CommentInline, StatusInline]


@admin.register(ApplicationComment)
class ApplicationCommentAdmin(admin.ModelAdmin):
    list_display = ("application", "user", "is_urgent", "created_at")
    list_filter = ("is_urgent",)
    search_fields = ("application__public_id", "user__email")


@admin.register(ApplicationStatusHistory)
class ApplicationStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("application", "old_status", "new_status", "changed_by", "created_at")
    search_fields = ("application__public_id", "old_status", "new_status")


@admin.register(DataConsent)
class DataConsentAdmin(admin.ModelAdmin):
    list_display = ("application", "user", "consent_type", "is_given", "given_at")
    list_filter = ("consent_type", "is_given")
    search_fields = ("application__public_id", "user__email")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "table_name", "record_id", "user", "timestamp")
    list_filter = ("action", "table_name")
    search_fields = ("record_id", "user__email")
    readonly_fields = ("timestamp",)
