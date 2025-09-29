"""Модели описания динамических анкет."""

from config.constants import (
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
from django.db import models


class Survey(models.Model):
    """Анкета, объединяющая набор шагов и вопросов."""

    code = models.SlugField("Код анкеты", max_length=SURVEY_CODE_MAX_LENGTH, unique=True)
    title = models.CharField(
        "Название анкеты",
        max_length=SURVEY_TITLE_MAX_LENGTH
    )
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
        choices=QType.choices
    )
    label = models.CharField(
        "Заголовок вопроса",
        max_length=QUESTION_LABEL_MAX_LENGTH,
    )
    required = models.BooleanField("Обязательный", default=False)
    payload = models.JSONField(
        "Дополнительные настройки",
        default=dict,
        blank=True
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
        max_length=10,
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
    label = models.CharField(
        "Название документа",
        max_length=DOCUMENT_LABEL_MAX_LENGTH
    )
    expression = models.JSONField(
        "Условие необходимости",
        null=True, blank=True
    )

    class Meta:
        verbose_name = "Требование по документу"
        verbose_name_plural = "Требования по документам"
        ordering = ("id",)

    def __str__(self) -> str:
        return f"{self.survey.code}:{self.code}"
