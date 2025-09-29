"""Модели пользовательских данных анкет."""

import uuid

from config.constants import STATUS_MAX_LENGTH
from django.conf import settings
from django.db import models

from .models_form import Question, Step, Survey


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
        max_length=STATUS_MAX_LENGTH,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    current_step = models.ForeignKey(
        Step,
        verbose_name="Текущий шаг",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="applications_current",
    )
    created_at = models.DateTimeField("Создана", auto_now_add=True)
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
