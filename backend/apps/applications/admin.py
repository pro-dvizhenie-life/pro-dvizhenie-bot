"""Регистрация моделей приложения заявок в админке."""

import json
from functools import lru_cache

from datetime import date, datetime

from django.contrib import admin
from django.db.models import Count, Prefetch, Q
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from .models import (
    Answer,
    Application,
    ApplicationComment,
    ApplicationStatusHistory,
    AuditLog,
    DataConsent,
    DocumentRequirement,
    Option,
    Question,
    Step,
    Survey,
)


class OptionInline(admin.TabularInline):

    model = Option
    extra = 0


class SurveyApplicationsFilter(admin.SimpleListFilter):
    title = "Заявки"
    parameter_name = "has_apps"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Есть заявки"),
            ("no", "Нет заявок"),
            ("active", "Есть активные"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "yes":
            return queryset.annotate(app_total=Count("applications", distinct=True)).filter(app_total__gt=0)
        if value == "no":
            return queryset.annotate(app_total=Count("applications", distinct=True)).filter(app_total=0)
        if value == "active":
            return queryset.annotate(
                app_active=Count(
                    "applications",
                    filter=~Q(applications__status=Application.Status.DRAFT),
                    distinct=True,
                )
            ).filter(app_active__gt=0)
        return queryset


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "title",
        "version",
        "is_active_badge",
        "steps_count",
        "questions_count",
        "requirements_count",
        "applications_stats",
        "quick_actions",
    )
    list_display_links = ("code", "title")
    list_filter = ("is_active", SurveyApplicationsFilter)
    search_fields = ("code", "title", "applications__public_id")
    search_help_text = "Поиск по коду анкеты, названию или публичному ID заявки"
    ordering = ("code", "version")
    actions = ("activate_surveys", "deactivate_surveys")
    readonly_fields = (
        "steps_overview",
        "steps_detail",
        "requirements_detail",
        "applications_overview",
        "applications_status_overview",
        "recent_applications",
    )
    fieldsets = (
        (None, {"fields": ("code", "title", "version", "is_active")} ),
        (
            "Структура анкеты",
            {
                "fields": ("steps_overview", "steps_detail", "requirements_detail"),
                "classes": ("collapse",),
            },
        ),
        (
            "Связанные заявки",
            {
                "fields": ("applications_overview", "applications_status_overview", "recent_applications"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        steps_qs = Step.objects.prefetch_related(
            Prefetch(
                "questions",
                queryset=Question.objects.only("id", "label", "code", "type", "required", "step_id"),
            ),
            Prefetch("outgoing_conditions"),
            Prefetch("incoming_conditions"),
        ).order_by("order")
        applications_qs = Application.objects.only("public_id", "status", "created_at").order_by("-created_at")
        requirements_qs = DocumentRequirement.objects.all()

        return queryset.prefetch_related(
            Prefetch("steps", queryset=steps_qs, to_attr="_prefetched_steps"),
            Prefetch("doc_requirements", queryset=requirements_qs, to_attr="_prefetched_requirements"),
            Prefetch("applications", queryset=applications_qs[:5], to_attr="_prefetched_recent_apps"),
        ).annotate(
            steps_total=Count("steps", distinct=True),
            questions_total=Count("steps__questions", distinct=True),
            requirements_total=Count("doc_requirements", distinct=True),
            applications_total=Count("applications", distinct=True),
            applications_active=Count(
                "applications",
                filter=~Q(applications__status=Application.Status.DRAFT),
                distinct=True,
            ),
        )

    def is_active_badge(self, obj):
        color = "#198754" if obj.is_active else "#6c757d"
        label = "Активна" if obj.is_active else "Не активна"
        return format_html(
            '<span style="padding:2px 8px;border-radius:999px;background:{};color:#fff;">{}</span>',
            color,
            label,
        )

    is_active_badge.short_description = "Статус"

    def steps_count(self, obj):
        return getattr(obj, "steps_total", obj.steps.count())

    steps_count.short_description = "Шагов"

    def questions_count(self, obj):
        return getattr(obj, "questions_total", sum(step.questions.count() for step in obj.steps.all()))

    questions_count.short_description = "Вопросов"

    def requirements_count(self, obj):
        return getattr(obj, "requirements_total", obj.doc_requirements.count())

    requirements_count.short_description = "Требований"

    def applications_stats(self, obj):
        total = getattr(obj, "applications_total", 0)
        active = getattr(obj, "applications_active", 0)
        return f"{active} активных / {total} всего"

    applications_stats.short_description = "Заявки"

    def quick_actions(self, obj):
        steps_url = f"{reverse('admin:applications_step_changelist')}?survey__id__exact={obj.pk}"
        questions_url = f"{reverse('admin:applications_question_changelist')}?step__survey__id__exact={obj.pk}"
        requirements_url = f"{reverse('admin:applications_documentrequirement_changelist')}?survey__id__exact={obj.pk}"
        applications_url = f"{reverse('admin:applications_application_changelist')}?survey__id__exact={obj.pk}"
        return format_html(
            '<a class="button" href="{}" target="_blank">Шаги</a> '
            '<a class="button" href="{}" target="_blank">Вопросы</a> '
            '<a class="button" href="{}" target="_blank">Документы</a> '
            '<a class="button" href="{}" target="_blank">Заявки</a>',
            steps_url,
            questions_url,
            requirements_url,
            applications_url,
        )

    quick_actions.short_description = "Быстрые действия"

    def steps_overview(self, obj):
        steps = getattr(obj, "steps_total", obj.steps.count())
        prefetched_steps = getattr(obj, "_prefetched_steps", None)
        if prefetched_steps:
            questions = sum(sum(1 for _ in step.questions.all()) for step in prefetched_steps)
        else:
            questions = getattr(obj, "questions_total", sum(step.questions.count() for step in obj.steps.all()))
        requirements = getattr(obj, "requirements_total", obj.doc_requirements.count())
        return format_html(
            "<ul style='margin:0;padding-left:18px;'>"
            "<li>Шагов: {}</li>"
            "<li>Вопросов: {}</li>"
            "<li>Требований документов: {}</li>"
            "</ul>",
            steps,
            questions,
            requirements,
        )

    steps_overview.short_description = "Структура анкеты"

    def applications_overview(self, obj):
        total = getattr(obj, "applications_total", 0)
        active = getattr(obj, "applications_active", 0)
        drafts = total - active
        return format_html(
            "<ul style='margin:0;padding-left:18px;'>"
            "<li>Всего заявок: {}</li>"
            "<li>Активных: {}</li>"
            "<li>Черновиков: {}</li>"
            "</ul>",
            total,
            active,
            drafts,
        )

    applications_overview.short_description = "Заявки"

    def applications_status_overview(self, obj):
        status_map = {key: 0 for key, _ in Application.Status.choices}
        aggregated = obj.applications.values("status").annotate(count=Count("id"))
        for entry in aggregated:
            status_map[entry["status"]] = entry["count"]
        rows = [f"<li>{label}: {status_map.get(key, 0)}</li>" for key, label in Application.Status.choices]
        return format_html("<ul style='margin:0;padding-left:18px;'>" + "".join(rows) + "</ul>")

    applications_status_overview.short_description = "По статусам"

    def recent_applications(self, obj):
        recent = getattr(obj, "_prefetched_recent_apps", None)
        if recent is None:
            recent = list(obj.applications.order_by("-created_at")[:5])
        if not recent:
            return "—"
        rows = []
        for application in recent:
            url = reverse("admin:applications_application_change", args=[application.pk])
            created_str = application.created_at.strftime("%Y-%m-%d %H:%M") if application.created_at else "—"
            rows.append(
                format_html(
                    '<li><a href="{}">{}</a> — {} ({})</li>',
                    url,
                    application.public_id,
                    application.get_status_display(),
                    created_str,
                )
            )
        return format_html("<ul style='margin:0;padding-left:18px;'>" + "".join(rows) + "</ul>")

    recent_applications.short_description = "Последние заявки"

    def steps_detail(self, obj):
        steps = getattr(obj, "_prefetched_steps", obj.steps.order_by("order"))
        if not steps:
            return "—"
        header = format_html(
            '<tr style="background:#f8f9fa;">'
            '<th style="padding:6px 10px;">Шаг</th>'
            '<th style="padding:6px 10px;">Код</th>'
            '<th style="padding:6px 10px;">Вопросов</th>'
            '<th style="padding:6px 10px;">Обязательных</th>'
            '<th style="padding:6px 10px;">Файлов</th>'
            '<th style="padding:6px 10px;">Условий</th>'
            '</tr>'
        )
        rows = []
        for step in steps:
            questions = list(step.questions.all())
            total = len(questions)
            required = sum(1 for q in questions if q.required)
            files = sum(1 for q in questions if q.type in {"file", "file_multi"})
            outgoing = list(step.outgoing_conditions.all())
            incoming = list(step.incoming_conditions.all())
            conditions = len(outgoing) + len(incoming)
            rows.append(
                format_html(
                    '<tr>'
                    '<td style="padding:6px 10px;">{}</td>'
                    '<td style="padding:6px 10px;">{}</td>'
                    '<td style="padding:6px 10px;text-align:center;">{}</td>'
                    '<td style="padding:6px 10px;text-align:center;">{}</td>'
                    '<td style="padding:6px 10px;text-align:center;">{}</td>'
                    '<td style="padding:6px 10px;text-align:center;">{}</td>'
                    '</tr>',
                    f"{step.order}. {step.title or step.code}",
                    step.code,
                    total,
                    required,
                    files,
                    conditions,
                )
            )
        body = format_html("".join(str(row) for row in rows))
        return format_html('<table style="width:100%;border-collapse:collapse;">{} {}</table>', header, body)

    steps_detail.short_description = "Шаги"

    def requirements_detail(self, obj):
        requirements = getattr(obj, "_prefetched_requirements", obj.doc_requirements.all())
        if not requirements:
            return "—"
        rows = [format_html('<li><strong>{}</strong> ({})</li>', req.label, req.code) for req in requirements]
        return format_html("<ul style='margin:0;padding-left:18px;'>" + "".join(rows) + "</ul>")

    requirements_detail.short_description = "Требования"

    @admin.action(description="Сделать анкеты активными")
    def activate_surveys(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Активировано анкет: {updated}")

    @admin.action(description="Сделать анкеты неактивными")
    def deactivate_surveys(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Деактивировано анкет: {updated}")

class StepConditionsFilter(admin.SimpleListFilter):
    title = "Условия"
    parameter_name = "has_conditions"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Есть условия"),
            ("no", "Без условий"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        queryset = queryset.annotate(
            cond_out=Count("outgoing_conditions", distinct=True),
            cond_in=Count("incoming_conditions", distinct=True),
        )
        if value == "yes":
            return queryset.filter(Q(cond_out__gt=0) | Q(cond_in__gt=0))
        if value == "no":
            return queryset.filter(cond_out=0, cond_in=0)
        return queryset


@admin.register(Step)
class StepAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "code",
        "title",
        "survey",
        "questions_count",
        "required_questions",
        "file_questions",
        "conditions_count",
        "quick_actions",
    )
    list_display_links = ("code", "title")
    list_filter = ("survey", StepConditionsFilter)
    search_fields = ("code", "title", "survey__code")
    search_help_text = "Поиск по коду шага, названию и анкете"
    ordering = ("survey", "order")
    readonly_fields = ("questions_overview",)
    fieldsets = (
        (None, {"fields": ("survey", "code", "title", "order")} ),
        ("Вопросы", {"fields": ("questions_overview",)}),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            questions_total=Count("questions", distinct=True),
            questions_required=Count("questions", filter=Q(questions__required=True), distinct=True),
            questions_files=Count("questions", filter=Q(questions__type__in=["file", "file_multi"]), distinct=True),
            conditions_out=Count("outgoing_conditions", distinct=True),
            conditions_in=Count("incoming_conditions", distinct=True),
        )

    def questions_count(self, obj):
        return getattr(obj, "questions_total", obj.questions.count())

    questions_count.short_description = "Вопросов"

    def required_questions(self, obj):
        return getattr(obj, "questions_required", obj.questions.filter(required=True).count())

    required_questions.short_description = "Обязательных"

    def file_questions(self, obj):
        return getattr(obj, "questions_files", obj.questions.filter(type__in=["file", "file_multi"]).count())

    file_questions.short_description = "Файлы"

    def conditions_count(self, obj):
        return getattr(obj, "conditions_out", 0) + getattr(obj, "conditions_in", 0)

    conditions_count.short_description = "Условий"

    def quick_actions(self, obj):
        questions_url = f"{reverse('admin:applications_question_changelist')}?step__id__exact={obj.pk}"
        survey_url = reverse("admin:applications_survey_change", args=[obj.survey.pk])
        return format_html(
            '<a class="button" href="{}" target="_blank">Вопросы</a> '
            '<a class="button" href="{}" target="_blank">Анкета</a>',
            questions_url,
            survey_url,
        )

    quick_actions.short_description = "Быстрые действия"

    def questions_overview(self, obj):
        questions = obj.questions.select_related(None).all()
        if not questions:
            return "Вопросы отсутствуют"
        rows = []
        for question in questions.order_by("id"):
            label = question.label or question.code
            required = "обязательный" if question.required else "не обязателен"
            rows.append(f"<li><strong>{label}</strong> — {question.get_type_display()} ({required})</li>")
        return format_html("<ul style='margin:0;'>" + "".join(rows) + "</ul>")

    questions_overview.short_description = "Список вопросов"


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("label", "step", "type", "required")
    list_filter = ("type", "required", "step__survey")
    search_fields = ("code", "label", "step__code")
    search_help_text = "Поиск по тексту вопроса, коду и коду шага"
    inlines = [OptionInline]


@admin.register(DocumentRequirement)
class DocumentRequirementAdmin(admin.ModelAdmin):
    list_display = ("label", "survey", "code")
    list_filter = ("survey",)
    search_fields = ("label", "code", "survey__code")


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


@lru_cache(maxsize=None)
def _option_labels(question_code: str) -> dict[str, str]:
    return {
        value: label
        for value, label in Option.objects.filter(question__code=question_code).values_list("value", "label")
    }


def _answer_value(obj: Application, code: str):
    if not hasattr(obj, "_answers_cache"):
        cached = getattr(obj, "_prefetched_answers", None)
        if cached is None:
            cached = list(obj.answers.select_related("question"))
        obj._answers_cache = {answer.question.code: answer for answer in cached}
    answer = obj._answers_cache.get(code)
    return answer.value if answer else None


class CityListFilter(admin.SimpleListFilter):
    title = "Город"
    parameter_name = "city"
    question_code = "q_city"

    def lookups(self, request, model_admin):
        raw_values = (
            Answer.objects.filter(question__code=self.question_code)
            .exclude(value__in=(None, "", [], {}))
            .values_list("value", flat=True)
        )
        choices = []
        seen = set()
        for value in raw_values:
            text = ApplicationAdmin._value_to_text(value).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            choices.append((text, text))
        choices.sort(key=lambda item: item[1].casefold())
        return choices

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset
        matching_ids = (
            Answer.objects.filter(question__code=self.question_code, value=value)
            .values_list("application_id", flat=True)
        )
        return queryset.filter(id__in=matching_ids)


class ApplicantBranchFilter(admin.SimpleListFilter):
    title = "Тип заявки"
    parameter_name = "branch"
    branches = {
        "adult": ("self", "relative"),
        "child": ("parent", "guardian"),
    }

    def lookups(self, request, model_admin):
        return ("adult", "Взрослый"), ("child", "Ребёнок")

    def queryset(self, request, queryset):
        branch = self.value()
        codes = self.branches.get(branch)
        if not codes:
            return queryset
        answer_ids = (
            Answer.objects.filter(question__code="q_who_fills", value__in=codes)
            .values_list("application_id", flat=True)
        )
        return queryset.filter(Q(applicant_type__in=codes) | Q(id__in=answer_ids)).distinct()


class DocumentsPresenceFilter(admin.SimpleListFilter):
    title = "Документы"
    parameter_name = "has_documents"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Есть документы"),
            ("no", "Нет документов"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "yes":
            return queryset.annotate(doc_count=Count("documents", distinct=True)).filter(doc_count__gt=0)
        if value == "no":
            return queryset.annotate(doc_count=Count("documents", distinct=True)).filter(doc_count=0)
        return queryset


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    search_question_codes = {"q_fullname", "q_contact_name", "q_city", "q_phone"}
    age_question_code = "q_dob"
    list_display = (
        "fio",
        "contact_person",
        "phone",
        "email",
        "city",
        "age_display",
        "status_badge",
        "stage_progress",
        "what_to_buy",
        "latest_comment",
        "quick_actions",
        "created_at",
        "submitted_at",
        "tsr_certificate",
    )
    list_display_links = ("fio",)
    ordering = ("-created_at",)
    list_filter = ("status", CityListFilter, ApplicantBranchFilter, DocumentsPresenceFilter, "current_stage", "submitted_at")
    search_fields = ("public_id",)
    inlines = [CommentInline, StatusInline]
    readonly_fields = ("answers_summary",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        answers_qs = Answer.objects.select_related("question")
        comments_qs = ApplicationComment.objects.select_related("user").order_by("-created_at")
        queryset = queryset.select_related("survey").annotate(total_steps=Count("survey__steps", distinct=True))
        return queryset.prefetch_related(
            Prefetch("answers", queryset=answers_qs, to_attr="_prefetched_answers"),
            Prefetch("comments", queryset=comments_qs, to_attr="_prefetched_comments"),
        )

    @staticmethod
    def _display_text(value):
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or "—"
        return value if value not in (None, "", [], {}) else "—"

    @staticmethod
    def _value_to_text(value) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (list, tuple, set)):
            return " ".join(ApplicationAdmin._value_to_text(item) for item in value)
        if isinstance(value, bool):
            return "Да" if value else "Нет"
        return str(value)

    def fio(self, obj):
        return self._display_text(_answer_value(obj, "q_fullname"))

    fio.short_description = "ФИО подопечного"

    def contact_person(self, obj):
        return self._display_text(_answer_value(obj, "q_contact_name"))

    contact_person.short_description = "Контактное лицо"

    def phone(self, obj):
        return self._display_text(_answer_value(obj, "q_phone"))

    phone.short_description = "Телефон"

    def email(self, obj):
        return self._display_text(_answer_value(obj, "q_email"))

    email.short_description = "Email"

    def city(self, obj):
        return self._display_text(_answer_value(obj, "q_city"))

    city.short_description = "Город"

    def age_display(self, obj):
        raw_value = _answer_value(obj, self.age_question_code)
        if not raw_value:
            return "—"
        if isinstance(raw_value, str):
            try:
                dob = datetime.strptime(raw_value, "%Y-%m-%d").date()
            except ValueError:
                return raw_value
        elif isinstance(raw_value, date):
            dob = raw_value
        else:
            return "—"
        today = date.today()
        years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if years < 0:
            return "—"
        return f"{years} лет"

    age_display.short_description = "Возраст"

    def status_badge(self, obj):
        label = obj.get_status_display()
        colors = {
            Application.Status.DRAFT: "#6c757d",
            Application.Status.SUBMITTED: "#0d6efd",
            Application.Status.UNDER_REVIEW: "#fd7e14",
            Application.Status.APPROVED: "#198754",
            Application.Status.REJECTED: "#dc3545",
        }
        try:
            status_enum = Application.Status(obj.status)
        except ValueError:
            status_enum = Application.Status.DRAFT
        color = colors.get(status_enum, "#6c757d")
        return format_html(
            '<span style="display:inline-block;padding:2px 8px;border-radius:999px;background-color:{};color:#fff;font-weight:600;">{}</span>',
            color,
            label,
        )

    status_badge.short_description = "Статус"
    status_badge.admin_order_field = "status"

    def what_to_buy(self, obj):
        value = _answer_value(obj, "q_what_to_buy")
        if not value:
            return "—"
        if isinstance(value, str):
            label = _option_labels("q_what_to_buy").get(value)
            return label or value
        return "—"

    what_to_buy.short_description = "Что нужно приобрести"

    def stage_progress(self, obj):
        total = getattr(obj, "total_steps", 0) or 0
        current = obj.current_stage or 0
        if total:
            return f"{min(current, total)}/{total}"
        return str(current)

    stage_progress.short_description = "Этапы"
    stage_progress.admin_order_field = "current_stage"

    def tsr_certificate(self, obj):
        value = _answer_value(obj, "q_tsr_certificate_has")
        if value in (None, ""):
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "да"}:
                return True
            if lowered in {"false", "0", "no", "нет"}:
                return False
        return None

    tsr_certificate.boolean = True
    tsr_certificate.short_description = "Есть сертификат на ТСР"

    def latest_comment(self, obj):
        comments = getattr(obj, "_prefetched_comments", None)
        if not comments:
            return "—"
        comment = comments[0]
        text = (comment.comment or "").strip()
        if len(text) > 80:
            text = f"{text[:77]}…"
        prefix = "[Срочно] " if comment.is_urgent else ""
        if not text and not comment.is_urgent:
            return "—"
        color = "#dc3545" if comment.is_urgent else "inherit"
        weight = "600" if comment.is_urgent else "400"
        return format_html(
            '<span style="color:{};font-weight:{};">{}{}</span>',
            color,
            weight,
            prefix,
            text,
        )

    latest_comment.short_description = "Последний комментарий"
    latest_comment.admin_order_field = "comments__created_at"

    def quick_actions(self, obj):
        detail_url = reverse("admin:applications_application_change", args=[obj.pk])
        documents_url = f"{reverse('admin:documents_document_changelist')}?application__id__exact={obj.pk}"
        comment_url = f"{reverse('admin:applications_applicationcomment_add')}?application={obj.pk}"
        return format_html(
            '<a class="button" href="{0}" target="_blank">Карточка</a> '
            '<a class="button" href="{1}" target="_blank">Документы</a> '
            '<a class="button" href="{2}">Комментарий</a>',
            detail_url,
            documents_url,
            comment_url,
        )

    quick_actions.short_description = "Быстрые действия"

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and "answers_summary" not in readonly:
            readonly.append("answers_summary")
        return readonly

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))
        if obj:
            fieldsets.append(("Ответы анкеты", {"fields": ("answers_summary",)}))
        return fieldsets

    @staticmethod
    def _answer_sort_key(answer):
        step = answer.question.step if answer.question else None
        step_order = getattr(step, "order", 0)
        question_payload = getattr(answer.question, "payload", {}) or {}
        question_order = question_payload.get("order") if isinstance(question_payload, dict) else None
        return (
            step_order,
            step.id if step else 0,
            question_order if isinstance(question_order, (int, float)) else answer.question.id,
        )

    @staticmethod
    def _format_answer_value(value):
        if value in (None, "", [], {}):
            return "—"
        if isinstance(value, bool):
            return "Да" if value else "Нет"
        if isinstance(value, list):
            rendered = ", ".join(
                json.dumps(item, ensure_ascii=False) if isinstance(item, dict) else ApplicationAdmin._value_to_text(item)
                for item in value
            )
            return rendered or "—"
        if isinstance(value, dict):
            pretty = json.dumps(value, ensure_ascii=False, indent=2)
            return format_html('<pre style="white-space: pre-wrap; margin: 0;">{}</pre>', pretty)
        if isinstance(value, str) and "\n" in value:
            return format_html('<pre style="white-space: pre-wrap; margin: 0;">{}</pre>', value)
        return ApplicationAdmin._value_to_text(value)

    def answers_summary(self, obj):
        answers = getattr(obj, "_prefetched_answers", None)
        if answers is None:
            answers = list(obj.answers.select_related("question__step"))
        if not answers:
            return "Ответов пока нет"
        sorted_answers = sorted(answers, key=self._answer_sort_key)
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
        body = format_html_join("", "{}", ((row,) for row in rows))
        return format_html(
            '<table class="admin-answers-table" style="width:100%;border-collapse:collapse;">{}</table>',
            body,
        )

    answers_summary.short_description = "Ответы анкеты"

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        cleaned_term = (search_term or "").strip()
        if not cleaned_term:
            return queryset, use_distinct

        raw_terms = cleaned_term.replace(",", " ").split()
        terms = [term for term in raw_terms if term]
        if not terms:
            terms = [cleaned_term]

        answers = list(
            Answer.objects.filter(question__code__in=self.search_question_codes)
            .values_list("application_id", "value")
        )

        if not answers:
            return queryset, use_distinct

        matching_ids = None
        for term in terms:
            term_cf = term.casefold()
            ids = {
                application_id
                for application_id, value in answers
                if term_cf in self._value_to_text(value).casefold()
            }
            if matching_ids is None:
                matching_ids = ids
            else:
                matching_ids &= ids
            if not matching_ids:
                break

        if matching_ids:
            queryset = queryset | self.model.objects.filter(id__in=matching_ids)
            use_distinct = True

        return queryset, use_distinct


@admin.register(ApplicationComment)
class ApplicationCommentAdmin(admin.ModelAdmin):
    answer_codes = {"q_fullname", "q_contact_name", "q_phone"}
    list_display = (
        "application_link",
        "applicant_name",
        "contact_person",
        "contact_phone",
        "comment_preview",
        "is_urgent",
        "user_display",
        "created_at",
    )
    list_display_links = ("application_link", "comment_preview")
    list_filter = ("is_urgent", "application__status", "user")
    search_fields = ("comment", "application__public_id", "user__email", "user__phone")
    actions = ("mark_not_urgent", "mark_as_urgent")
    exclude = ("user",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        answers_qs = Answer.objects.filter(question__code__in=self.answer_codes).select_related("question")
        return queryset.select_related("application", "user").prefetch_related(
            Prefetch("application__answers", queryset=answers_qs, to_attr="_prefetched_answers")
        )

    def application_link(self, obj):
        return obj.application.public_id

    application_link.short_description = "Заявка"

    def applicant_name(self, obj):
        return ApplicationAdmin._display_text(_answer_value(obj.application, "q_fullname"))

    applicant_name.short_description = "ФИО подопечного"

    def contact_person(self, obj):
        return ApplicationAdmin._display_text(_answer_value(obj.application, "q_contact_name"))

    contact_person.short_description = "Контактное лицо"

    def contact_phone(self, obj):
        return ApplicationAdmin._display_text(_answer_value(obj.application, "q_phone"))

    contact_phone.short_description = "Телефон"

    def comment_preview(self, obj):
        text = (obj.comment or "").strip()
        if len(text) > 80:
            return f"{text[:77]}…"
        return text or "—"

    comment_preview.short_description = "Комментарий"
    comment_preview.admin_order_field = "comment"

    def user_display(self, obj):
        user = obj.user
        if not user:
            return "—"
        if user.role == "applicant":
            return "—"
        email = (user.email or "").strip()
        phone = (user.phone or "").strip()
        if email and phone:
            return f"{email} / {phone}"
        full_name = getattr(user, "get_full_name", None)
        if callable(full_name):
            resolved = full_name()
            if resolved:
                return resolved
        return email or phone or str(user)

    user_display.short_description = "Автор"

    def mark_not_urgent(self, request, queryset):
        updated = queryset.update(is_urgent=False)
        self.message_user(request, f"Снята отметка ‘Срочно’ у {updated} комментариев")

    mark_not_urgent.short_description = "Снять ‘Срочно’"

    def mark_as_urgent(self, request, queryset):
        updated = queryset.update(is_urgent=True)
        self.message_user(request, f"Помечено ‘Срочно’ {updated} комментариев")

    mark_as_urgent.short_description = "Отметить как ‘Срочно’"

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        cleaned_term = (search_term or "").strip()
        if not cleaned_term:
            return queryset, use_distinct

        raw_terms = cleaned_term.replace(",", " ").split()
        terms = [term for term in raw_terms if term]
        if not terms:
            terms = [cleaned_term]

        answer_pairs = list(
            Answer.objects.filter(question__code__in=self.answer_codes)
            .values_list("application_id", "value")
        )

        application_ids: set[int] = set()

        if answer_pairs:
            matching = None
            for term in terms:
                term_cf = term.casefold()
                ids = {
                    application_id
                    for application_id, value in answer_pairs
                    if term_cf in ApplicationAdmin._value_to_text(value).casefold()
                }
                if matching is None:
                    matching = ids
                else:
                    matching &= ids
                if matching is not None and not matching:
                    break
            if matching:
                application_ids.update(matching)

        if application_ids:
            queryset = queryset | self.model.objects.filter(application__id__in=application_ids)
            use_distinct = True

        return queryset, use_distinct

    def save_model(self, request, obj, form, change):
        if not change or obj.user_id is None:
            obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(ApplicationStatusHistory)
class ApplicationStatusHistoryAdmin(admin.ModelAdmin):
    answer_codes = {"q_fullname"}
    list_display = (
        "application_link",
        "applicant_name",
        "old_status_display",
        "new_status_display",
        "changed_by_display",
        "created_at",
    )
    list_filter = ("new_status", "old_status")
    search_fields = ("application__public_id", "changed_by__email")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        answers_qs = Answer.objects.filter(question__code__in=self.answer_codes).select_related("question")
        return queryset.select_related("application", "changed_by").prefetch_related(
            Prefetch("application__answers", queryset=answers_qs, to_attr="_prefetched_answers")
        )

    def application_link(self, obj):
        return obj.application.public_id

    application_link.short_description = "Заявка"

    def applicant_name(self, obj):
        return ApplicationAdmin._display_text(_answer_value(obj.application, "q_fullname"))

    applicant_name.short_description = "ФИО подопечного"

    def old_status_display(self, obj):
        return Application.Status(obj.old_status).label if obj.old_status else "—"

    old_status_display.short_description = "Был"
    old_status_display.admin_order_field = "old_status"

    def new_status_display(self, obj):
        return Application.Status(obj.new_status).label if obj.new_status else "—"

    new_status_display.short_description = "Стал"
    new_status_display.admin_order_field = "new_status"

    def changed_by_display(self, obj):
        if obj.changed_by:
            email = (obj.changed_by.email or "").strip()
            phone = (obj.changed_by.phone or "").strip()
            if email and phone:
                return f"{email} / {phone}"
            return email or phone or obj.changed_by.get_full_name() or str(obj.changed_by)
        return "Система"

    changed_by_display.short_description = "Изменил"

@admin.register(DataConsent)
class DataConsentAdmin(admin.ModelAdmin):
    answer_codes = {"q_fullname", "q_contact_name", "q_phone", "q_email"}
    list_display = (
        "applicant_name",
        "contact_person",
        "contact_phone",
        "contact_email",
        "consent_type_display",
        "is_given",
        "given_at",
        "user_display",
    )
    list_filter = ("consent_type", "is_given")
    search_fields = ("application__public_id", "user__email", "user__phone")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        answers_qs = Answer.objects.filter(question__code__in=self.answer_codes).select_related("question")
        return queryset.select_related("user", "application").prefetch_related(
            Prefetch("application__answers", queryset=answers_qs, to_attr="_prefetched_answers")
        )

    def applicant_name(self, obj):
        value = _answer_value(obj.application, "q_fullname")
        return ApplicationAdmin._display_text(value)

    applicant_name.short_description = "ФИО подопечного"

    def contact_person(self, obj):
        value = _answer_value(obj.application, "q_contact_name")
        return ApplicationAdmin._display_text(value)

    contact_person.short_description = "Контактное лицо"

    def contact_phone(self, obj):
        value = _answer_value(obj.application, "q_phone")
        return ApplicationAdmin._display_text(value)

    contact_phone.short_description = "Телефон"

    def contact_email(self, obj):
        value = _answer_value(obj.application, "q_email")
        return ApplicationAdmin._display_text(value)

    contact_email.short_description = "Email"

    def consent_type_display(self, obj):
        return obj.get_consent_type_display()

    consent_type_display.short_description = "Тип согласия"
    consent_type_display.admin_order_field = "consent_type"

    def user_display(self, obj):
        email = (obj.user.email or "").strip()
        phone = (obj.user.phone or "").strip()
        if email and phone:
            return f"{email} / {phone}"
        return email or phone or "—"

    user_display.short_description = "Пользователь"

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        cleaned_term = (search_term or "").strip()
        if not cleaned_term:
            return queryset, use_distinct

        raw_terms = cleaned_term.replace(",", " ").split()
        terms = [term for term in raw_terms if term]
        if not terms:
            terms = [cleaned_term]

        application_ids = set()

        for term in terms:
            django_filter = (Q(user__email__icontains=term) | Q(user__phone__icontains=term))
            application_ids.update(
                queryset.filter(django_filter).values_list("application_id", flat=True)
            )

        answer_pairs = list(
            Answer.objects.filter(question__code__in=self.answer_codes)
            .values_list("application_id", "value")
        )

        if answer_pairs:
            answer_matching = None
            for term in terms:
                term_cf = term.casefold()
                ids = {
                    application_id
                    for application_id, value in answer_pairs
                    if term_cf in ApplicationAdmin._value_to_text(value).casefold()
                }
                if answer_matching is None:
                    answer_matching = ids
                else:
                    answer_matching &= ids
                if answer_matching is not None and not answer_matching:
                    break

            if answer_matching:
                application_ids.update(answer_matching)

        if application_ids:
            queryset = queryset | self.model.objects.filter(application__id__in=application_ids)
            use_distinct = True

        return queryset, use_distinct


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    action_labels = {
        "create": "Создание",
        "insert": "Создание",
        "update": "Изменение",
        "delete": "Удаление",
        "submit": "Отправка",
        "status_change": "Смена статуса",
        "login": "Вход",
        "logout": "Выход",
    }
    table_labels = {
        "applications": "Заявка",
        "applications_application": "Заявка",
        "applications_applicationcomment": "Комментарий",
        "applications_dataconsent": "Согласие",
        "applications_applicationstatushistory": "История статуса",
        "documents_document": "Документ",
    }
    table_admin_urls = {
        "applications": "applications_application_change",
        "applications_application": "applications_application_change",
        "applications_applicationcomment": "applications_applicationcomment_change",
        "applications_dataconsent": "applications_dataconsent_change",
        "applications_applicationstatushistory": "applications_applicationstatushistory_change",
        "documents_document": "documents_document_change",
    }

    list_display = (
        "timestamp",
        "action_verbose",
        "table_verbose",
        "record_link",
        "user_display",
        "description",
        "ip_address",
    )
    list_filter = ("action", "table_name", "user")
    search_fields = ("record_id", "user__email", "user__phone", "ip_address")
    readonly_fields = ("timestamp", "description", "record_link")
    date_hierarchy = "timestamp"

    def action_verbose(self, obj):
        return self.action_labels.get(obj.action, obj.action)

    action_verbose.short_description = "Действие"
    action_verbose.admin_order_field = "action"

    def table_verbose(self, obj):
        return self.table_labels.get(obj.table_name, obj.table_name or "—")

    table_verbose.short_description = "Объект"
    table_verbose.admin_order_field = "table_name"

    def record_link(self, obj):
        if not obj.record_id:
            return "—"
        url_name = self.table_admin_urls.get(obj.table_name)
        if not url_name:
            return str(obj.record_id)
        try:
            url = reverse(f"admin:{url_name}", args=[obj.record_id])
        except Exception:
            return str(obj.record_id)
        return format_html('<a href="{}">{}</a>', url, obj.record_id)

    record_link.short_description = "ID / ссылка"

    def user_display(self, obj):
        if not obj.user:
            return "Система"
        email = (obj.user.email or "").strip()
        phone = (obj.user.phone or "").strip()
        if email and phone:
            return f"{email} / {phone}"
        return email or phone or str(obj.user)

    user_display.short_description = "Пользователь"
    user_display.admin_order_field = "user"

    def description(self, obj):
        action = self.action_labels.get(obj.action, obj.action or "Действие")
        table = self.table_labels.get(obj.table_name, obj.table_name or "Запись")
        record = str(obj.record_id) if obj.record_id else ""
        summary = f"{table} {record}".strip()
        if summary:
            summary = f"{summary}: {action.lower()}" if action else summary
        else:
            summary = action
        user_part = self.user_display(obj)
        if user_part and user_part != "Система":
            summary = f"{summary} (сотрудник: {user_part})"
        return summary or "—"

    description.short_description = "Описание"
