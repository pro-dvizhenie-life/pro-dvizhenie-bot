"""Настройки админки для управления анкетами и заявками."""

from django.contrib import admin

from .models_data import Answer, Application
from .models_form import Condition, DocumentRequirement, Option, Question, Step, Survey


class OptionInline(admin.TabularInline):
    """Встроенная форма вариантов ответа."""

    model = Option
    extra = 0


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    """Админ-панель анкет."""

    list_display = ("code", "title", "version", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "title")


@admin.register(Step)
class StepAdmin(admin.ModelAdmin):
    """Админ-панель шагов анкеты."""

    list_display = ("code", "survey", "order")
    list_filter = ("survey",)
    search_fields = ("code", "title", "survey__code")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Админ-панель вопросов с инлайнами вариантов."""

    inlines = [OptionInline]
    list_display = ("code", "step", "type", "required")
    list_filter = ("type", "required", "step__survey")
    search_fields = ("code", "label", "step__code")


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    """Админ-панель вариантов ответа."""

    list_display = ("question", "value", "label", "order")
    list_filter = ("question__step__survey",)
    search_fields = ("value", "label", "question__code")


@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    """Админ-панель условий показа."""

    list_display = ("survey", "scope", "question", "from_step", "goto_step")
    list_filter = ("scope", "survey")
    search_fields = ("survey__code",)


@admin.register(DocumentRequirement)
class DocumentRequirementAdmin(admin.ModelAdmin):
    """Админ-панель требований к документам."""

    list_display = ("survey", "code", "label")
    list_filter = ("survey",)
    search_fields = ("code", "label")


class AnswerInline(admin.TabularInline):
    """Readonly-инлайн ответов в карточке заявки."""

    model = Answer
    extra = 0
    can_delete = False
    readonly_fields = ("question", "value", "updated_at")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    """Админ-панель заявок с привязанными ответами."""

    inlines = [AnswerInline]
    list_display = (
        "public_id",
        "survey",
        "status",
        "current_step",
        "created_at",
        "submitted_at",
    )
    list_filter = ("status", "survey")
    search_fields = ("public_id",)


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    """Админ-панель отдельных ответов."""

    list_display = ("application", "question", "updated_at")
    list_filter = ("question__step__survey",)
    search_fields = ("application__public_id", "question__code")
