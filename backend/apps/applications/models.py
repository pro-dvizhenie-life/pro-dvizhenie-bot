"""Модели динамических анкет и пользовательских заявок."""

from __future__ import annotations

import uuid

from config.constants import (
    APPLICANT_TYPE_MAX_LENGTH,
    APPLICATION_STATUS_MAX_LENGTH,
    AUDIT_ACTION_MAX_LENGTH,
    AUDIT_TABLE_MAX_LENGTH,
    CONSENT_TYPE_MAX_LENGTH,
    DOCUMENT_LABEL_MAX_LENGTH,
    OPTION_LABEL_MAX_LENGTH,
    OPTION_ORDER_DEFAULT,
    OPTION_VALUE_MAX_LENGTH,
    QUESTION_CODE_MAX_LENGTH,
    QUESTION_LABEL_MAX_LENGTH,
    QUESTION_TYPE_MAX_LENGTH,
    STEP_CODE_MAX_LENGTH,
    STEP_TITLE_MAX_LENGTH,
    SURVEY_CODE_MAX_LENGTH,
    SURVEY_TITLE_MAX_LENGTH,
)
from django.conf import settings
from django.db import models


class Survey(models.Model):
    """Анкета, объединяющая набор шагов и вопросов."""

    code = models.SlugField(
        "Код анкеты",
        max_length=SURVEY_CODE_MAX_LENGTH,
        unique=True,
    )
    title = models.CharField("Название анкеты", max_length=SURVEY_TITLE_MAX_LENGTH)
    version = models.PositiveIntegerField("Версия", default=1)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Анкета"
        verbose_name_plural = "Анкеты"
        ordering = ("code", "id")

    def __str__(self) -> str:
        return f"{self.code} v{self.version}"


class Step(models.Model):
    """Шаг анкеты, включающий несколько вопросов."""

    survey = models.ForeignKey(
        Survey,
        verbose_name="Анкета",
        on_delete=models.CASCADE,
        related_name="steps",
    )
    code = models.SlugField("Код шага", max_length=STEP_CODE_MAX_LENGTH)
    title = models.CharField("Название шага", max_length=STEP_TITLE_MAX_LENGTH)
    order = models.PositiveIntegerField("Порядок показа")

    class Meta:
        unique_together = (("survey", "code"),)
        ordering = ("order", "id")
        verbose_name = "Шаг"
        verbose_name_plural = "Шаги"

    def __str__(self) -> str:
        return f"{self.survey.code}:{self.code}"


class Question(models.Model):
    """Вопрос внутри шага анкеты."""

    class QType(models.TextChoices):
        TEXT = "text", "Текст"
        NUMBER = "number", "Число"
        DATE = "date", "Дата"
        SELECT_ONE = "select_one", "Один из списка"
        SELECT_MANY = "select_many", "Несколько из списка"
        YES_NO = "yes_no", "Да/Нет"
        FILE = "file", "Файл"

    step = models.ForeignKey(
        Step,
        verbose_name="Шаг",
        on_delete=models.CASCADE,
        related_name="questions",
    )
    code = models.SlugField("Код вопроса", max_length=QUESTION_CODE_MAX_LENGTH)
    type = models.CharField(
        "Тип вопроса",
        max_length=QUESTION_TYPE_MAX_LENGTH,
        choices=QType.choices,
    )
    label = models.CharField("Заголовок вопроса", max_length=QUESTION_LABEL_MAX_LENGTH)
    required = models.BooleanField("Обязательный", default=False)
    payload = models.JSONField(
        "Дополнительные настройки",
        default=dict,
        blank=True,
    )

    class Meta:
        unique_together = (("step", "code"),)
        ordering = ("id",)
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"

    def __str__(self) -> str:
        return f"{self.step.code}:{self.code}"


class Option(models.Model):
    """Вариант ответа на вопрос закрытого типа."""

    question = models.ForeignKey(
        Question,
        verbose_name="Вопрос",
        on_delete=models.CASCADE,
        related_name="options",
    )
    value = models.CharField("Значение", max_length=OPTION_VALUE_MAX_LENGTH)
    label = models.CharField("Подпись", max_length=OPTION_LABEL_MAX_LENGTH)
    order = models.PositiveIntegerField("Порядок", default=OPTION_ORDER_DEFAULT)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "Вариант ответа"
        verbose_name_plural = "Варианты ответа"

    def __str__(self) -> str:
        return f"{self.question.code}:{self.value}"


class Condition(models.Model):
    """Условие JSON-logic для показа вопросов или переходов между шагами."""

    survey = models.ForeignKey(
        Survey,
        verbose_name="Анкета",
        on_delete=models.CASCADE,
        related_name="conditions",
    )
    scope = models.CharField(
        "Область применения",
        max_length=QUESTION_TYPE_MAX_LENGTH,
        choices=(("question", "question"), ("step", "step")),
    )
    expression = models.JSONField("Выражение JSON-logic")
    question = models.ForeignKey(
        Question,
        verbose_name="Вопрос",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="visibility_conditions",
    )
    from_step = models.ForeignKey(
        Step,
        verbose_name="Исходный шаг",
        null=True,
        blank=True,
        related_name="outgoing_conditions",
        on_delete=models.CASCADE,
    )
    goto_step = models.ForeignKey(
        Step,
        verbose_name="Следующий шаг",
        null=True,
        blank=True,
        related_name="incoming_conditions",
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = "Условие показа"
        verbose_name_plural = "Условия показа"
        ordering = ("id",)

    def __str__(self) -> str:
        return f"{self.survey.code}:{self.scope}:{self.id}"


class DocumentRequirement(models.Model):
    """Правило необходимости документа в зависимости от ответов."""

    survey = models.ForeignKey(
        Survey,
        verbose_name="Анкета",
        on_delete=models.CASCADE,
        related_name="doc_requirements",
    )
    code = models.SlugField("Код требования", max_length=QUESTION_CODE_MAX_LENGTH)
    label = models.CharField("Название документа", max_length=DOCUMENT_LABEL_MAX_LENGTH)
    expression = models.JSONField("Условие необходимости", null=True, blank=True)

    class Meta:
        verbose_name = "Требование по документу"
        verbose_name_plural = "Требования по документам"
        ordering = ("id",)

    def __str__(self) -> str:
        return f"{self.survey.code}:{self.code}"


class Application(models.Model):
    """Заявка пользователя и прогресс её заполнения."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        SUBMITTED = "submitted", "Отправлена"
        UNDER_REVIEW = "under_review", "На рассмотрении"
        APPROVED = "approved", "Одобрена"
        REJECTED = "rejected", "Отклонена"

    public_id = models.UUIDField(
        "Публичный идентификатор",
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Пользователь",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="applications",
    )
    survey = models.ForeignKey(
        Survey,
        verbose_name="Анкета",
        on_delete=models.PROTECT,
        related_name="applications",
    )
    status = models.CharField(
        "Статус",
        max_length=APPLICATION_STATUS_MAX_LENGTH,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    applicant_type = models.CharField(
        "Тип заявителя",
        max_length=APPLICANT_TYPE_MAX_LENGTH,
        blank=True,
    )
    current_step = models.ForeignKey(
        Step,
        verbose_name="Текущий шаг",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="applications_current",
    )
    current_stage = models.IntegerField("Текущий этап", default=0)
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлена", auto_now=True)
    submitted_at = models.DateTimeField("Отправлена", null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"

    def __str__(self) -> str:
        return f"{self.public_id} ({self.survey.code})"


class Answer(models.Model):
    """Ответ пользователя на конкретный вопрос."""

    application = models.ForeignKey(
        Application,
        verbose_name="Заявка",
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        Question,
        verbose_name="Вопрос",
        on_delete=models.CASCADE,
        related_name="answers",
    )
    value = models.JSONField("Значение")
    updated_at = models.DateTimeField("Изменён", auto_now=True)

    class Meta:
        unique_together = (("application", "question"),)
        verbose_name = "Ответ"
        verbose_name_plural = "Ответы"
        ordering = ("-updated_at", "id")

    def __str__(self) -> str:
        return f"{self.application.public_id}:{self.question.code}"


class ApplicationComment(models.Model):
    """Комментарий по заявке от сотрудника или пользователя."""

    application = models.ForeignKey(
        Application,
        verbose_name="Заявка",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Автор",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="application_comments",
    )
    comment = models.TextField("Комментарий")
    is_urgent = models.BooleanField("Срочно", default=False)
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"
        ordering = ("-created_at", "id")

    def __str__(self) -> str:
        return f"{self.application.public_id}:{self.created_at:%Y-%m-%d %H:%M}"


class ApplicationStatusHistory(models.Model):
    """История смен статусов заявки."""

    application = models.ForeignKey(
        Application,
        verbose_name="Заявка",
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    old_status = models.CharField(
        "Старый статус",
        max_length=APPLICATION_STATUS_MAX_LENGTH,
    )
    new_status = models.CharField(
        "Новый статус",
        max_length=APPLICATION_STATUS_MAX_LENGTH,
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Изменён пользователем",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="status_changes",
    )
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "История статуса"
        verbose_name_plural = "Истории статусов"
        ordering = ("-created_at", "id")

    def __str__(self) -> str:
        return f"{self.application.public_id}:{self.old_status}->{self.new_status}"


class DataConsent(models.Model):
    """Согласие на обработку данных."""

    class CType(models.TextChoices):
        PDN_152 = "pdn_152", "Персональные данные (152-ФЗ)"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Пользователь",
        on_delete=models.CASCADE,
        related_name="data_consents",
    )
    application = models.ForeignKey(
        Application,
        verbose_name="Заявка",
        on_delete=models.CASCADE,
        related_name="consents",
    )
    consent_type = models.CharField(
        "Тип согласия",
        max_length=CONSENT_TYPE_MAX_LENGTH,
        choices=CType.choices,
        default=CType.PDN_152,
    )
    is_given = models.BooleanField("Дано", default=False)
    given_at = models.DateTimeField("Дата согласия", null=True, blank=True)
    ip_address = models.GenericIPAddressField("IP-адрес", null=True, blank=True)

    class Meta:
        unique_together = (("user", "application", "consent_type"),)
        verbose_name = "Согласие"
        verbose_name_plural = "Согласия"
        ordering = ("-given_at", "id")

    def __str__(self) -> str:
        return f"{self.application.public_id}:{self.consent_type}"


class AuditLog(models.Model):
    """Журнал аудита действий пользователей."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Пользователь",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField("Действие", max_length=AUDIT_ACTION_MAX_LENGTH)
    table_name = models.CharField("Таблица", max_length=AUDIT_TABLE_MAX_LENGTH)
    record_id = models.UUIDField("ID записи", null=True, blank=True)
    ip_address = models.GenericIPAddressField("IP-адрес", null=True, blank=True)
    timestamp = models.DateTimeField("Время", auto_now_add=True)

    class Meta:
        verbose_name = "Запись аудита"
        verbose_name_plural = "Журнал аудита"
        ordering = ("-timestamp", "id")
        indexes = [models.Index(fields=["table_name", "timestamp"])]

    def __str__(self) -> str:
        return f"{self.action}:{self.table_name}:{self.timestamp:%Y-%m-%d %H:%M}"


__all__ = [
    "Survey",
    "Step",
    "Question",
    "Option",
    "Condition",
    "DocumentRequirement",
    "Application",
    "Answer",
    "ApplicationComment",
    "ApplicationStatusHistory",
    "DataConsent",
    "AuditLog",
]
