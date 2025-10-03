"""Основной сценарий Telegram-бота, ведущий пользователя по анкете."""

from __future__ import annotations

import logging
import mimetypes
from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Optional, Tuple

from applications.models import Answer, Application, Question, Step, Survey
from applications.services.application_service import (
    CONSENT_DECLINED_MESSAGE,
    ensure_applicant_account,
    handle_consent_decline,
    record_consent,
)
from applications.services.form_runtime import (
    build_answer_dict,
    next_step,
    validate_answer_value,
    visible_questions,
)
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from documents.services import complete_upload, get_storage, request_upload
from documents.storages import DocumentStorageError

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes


logger = logging.getLogger(__name__)

CONSENT_QUESTION_CODE = "q_agree"
SKIP_CALLBACK_VALUE = "__skip__"
SKIPPED_SENTINEL = {"skipped": True}
AUTO_FILL_DATE_QUESTIONS = {"q_application_date"}


@dataclass
class ActiveQuestion:
    """Контейнер для следующего вопроса, ожидающего ответа."""

    question: Question
    step: Step
    answers: dict[str, Any]


class DocumentIngestionError(RuntimeError):
    """Возникает, если файл из Telegram не удалось сохранить."""


class DefaultScenario:
    """Сценарий диалога, использующий динамическую анкету проекта."""

    def __init__(self, survey_code: str = "default") -> None:
        """Запоминает код анкеты, с которой работает бот."""

        self.survey_code = survey_code

    async def handle_start(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Приветствует пользователя и запускает процесс анкеты."""

        chat = update.effective_chat
        telegram_user = update.effective_user
        if not chat or not telegram_user:
            return
        try:
            await context.bot.delete_my_commands()
        except Exception:  # pragma: no cover - вспомогательная очистка, не критично
            logger.debug("Не удалось очистить меню команд", exc_info=True)
        logger.debug("handle_start chat=%s user=%s", getattr(chat, "id", None), getattr(telegram_user, "id", None))
        django_user = await self._ensure_user(telegram_user)
        application = await self._ensure_application(django_user)
        greeting = (
            "Здравствуйте! Я помогу заполнить заявку фонда «Движение Жизни».\n"
            "Отвечайте на вопросы по очереди. Для необязательных полей можно написать «пропустить»."
        )
        await context.bot.send_message(chat_id=chat.id, text=greeting)
        await self._prompt_next_question(chat.id, application, context)

    async def handle_help(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Показывает подсказку по командам и процессу заполнения."""

        chat = update.effective_chat
        if not chat:
            return
        help_text = (
            "Продолжайте заполнять анкету, отвечая на сообщения бота.\n"
            "Команды:\n"
            "• /start — начать или продолжить заполнение\n"
            "• /help — показать подсказку\n"
            "Используйте кнопки под сообщениями для вариантов выбора."
        )
        await context.bot.send_message(chat_id=chat.id, text=help_text)

    async def handle_text(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Обрабатывает свободный текст пользователя как ответ на вопрос."""

        message = update.effective_message
        telegram_user = update.effective_user
        chat = update.effective_chat
        if not message or not telegram_user or not chat:
            return
        logger.debug(
            "handle_text chat=%s user=%s text=%s",
            getattr(chat, "id", None),
            getattr(telegram_user, "id", None),
            message.text,
        )
        text = (message.text or "").strip()
        django_user = await self._ensure_user(telegram_user)
        application = await self._ensure_application(django_user)
        active = await self._resolve_active_question(application)
        if active is None:
            await message.reply_text(
                "Анкета уже заполнена. Если хотите начать заново, используйте команду /start."
            )
            return
        question = active.question
        if self._should_skip(text) and not question.required:
            await self._save_answer(application, question, None)
            await self._after_answer(chat.id, application, context)
            return
        prepared, error = await self._prepare_freeform_input(question, text)
        if error:
            await message.reply_text(error)
            return
        normalized, validation_error = await self._validate_answer(question, prepared)
        if validation_error:
            await message.reply_text(validation_error)
            return
        if question.code == CONSENT_QUESTION_CODE and normalized is False:
            await message.reply_text(CONSENT_DECLINED_MESSAGE)
            await self._finalize_consent_decline(application)
            return
        await self._save_answer(application, question, normalized)
        await self._after_answer(chat.id, application, context)

    async def handle_callback(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Обрабатывает нажатия на inline-кнопки и обновляет состояние."""

        query = update.callback_query
        telegram_user = update.effective_user
        chat = update.effective_chat
        if not query or not telegram_user or not chat:
            return
        logger.debug(
            "handle_callback chat=%s user=%s data=%s",
            getattr(chat, "id", None),
            getattr(telegram_user, "id", None),
            getattr(query, "data", None),
        )
        await query.answer()
        django_user = await self._ensure_user(telegram_user)
        application = await self._ensure_application(django_user)
        code, raw_value = self._parse_callback_payload(query.data or "")
        if not code:
            await query.edit_message_text("Не удалось обработать ответ, попробуйте ещё раз.")
            return
        if code == "__restart__":
            await query.edit_message_text("Начинаем новую анкету!")
            application = await self._restart_application(application)
            await self._prompt_next_question(chat.id, application, context)
            return

        question = await self._get_question(application, code)
        if question is None:
            await query.edit_message_text("Этот вопрос сейчас недоступен.")
            return
        if raw_value == SKIP_CALLBACK_VALUE:
            await query.edit_message_text("Хорошо, пропускаем этот документ.")
            await self._save_answer(application, question, SKIPPED_SENTINEL.copy())
            await self._after_answer(chat.id, application, context)
            return
        prepared = self._prepare_choice_input(question, raw_value)
        normalized, error = await self._validate_answer(question, prepared)
        if error:
            await query.edit_message_text(error)
            return
        if question.code == CONSENT_QUESTION_CODE and normalized is False:
            await query.edit_message_text(CONSENT_DECLINED_MESSAGE)
            await self._finalize_consent_decline(application)
            return
        await self._save_answer(application, question, normalized)
        await self._after_answer(chat.id, application, context)

    async def handle_document(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Принимает файлы из Telegram и сохраняет их в анкету."""

        message = update.effective_message
        telegram_user = update.effective_user
        chat = update.effective_chat
        if not message or not telegram_user or not chat:
            return
        django_user = await self._ensure_user(telegram_user)
        application = await self._ensure_application(django_user)
        active = await self._resolve_active_question(application)
        if active is None:
            await message.reply_text(
                "Анкета завершена. Если нужно обновить документы, начните заново с /start."
            )
            return
        question = active.question
        payload = self._extract_file_payload(message)
        if payload is None:
            await message.reply_text("Отправьте документ или фотографию как вложение.")
            return
        if question.type not in {Question.QType.FILE, Question.QType.FILE_MULTI}:
            await message.reply_text("Сейчас нужен текстовый ответ. Используйте кнопки или напишите сообщение.")
            return
        try:
            document_id = await self._ingest_document(application, question, payload, context)
        except DocumentIngestionError as exc:
            await message.reply_text(str(exc))
            return
        existing = active.answers.get(question.code)
        if question.type == Question.QType.FILE_MULTI:
            items: list[str]
            if isinstance(existing, list):
                items = [str(item) for item in existing]
            elif isinstance(existing, str) and existing:
                items = [existing]
            else:
                items = []
            items.append(document_id)
            value: Any = items
        else:
            value = document_id
        await self._save_answer(application, question, value)
        await message.reply_text("Документ сохранён.")
        await self._after_answer(chat.id, application, context)

    async def _ensure_user(self, telegram_user) -> Any:
        """Находит или создаёт Django-пользователя для Telegram-аккаунта."""

        return await sync_to_async(self._ensure_user_sync, thread_sensitive=True)(telegram_user)

    async def _ensure_application(self, user: Any) -> Application:
        """Создаёт или возвращает активную заявку пользователя."""

        return await sync_to_async(self._ensure_application_sync, thread_sensitive=True)(user)

    async def _resolve_active_question(self, application: Application) -> Optional[ActiveQuestion]:
        """Возвращает следующий вопрос, который нужно задать пользователю."""

        return await sync_to_async(
            self._resolve_active_question_sync,
            thread_sensitive=True,
        )(application)

    async def _save_answer(self, application: Application, question: Question, value: Any) -> None:
        """Сохраняет ответ пользователя в хранилище анкет."""

        await sync_to_async(self._save_answer_sync, thread_sensitive=True)(application, question, value)

    async def _restart_application(self, application: Application) -> Application:
        """Пересоздаёт заявку после запроса пользователя."""

        return await sync_to_async(self._restart_application_sync, thread_sensitive=True)(application)

    async def _get_question(self, application: Application, code: str) -> Optional[Question]:
        """Ищет вопрос по коду внутри текущей заявки."""

        return await sync_to_async(self._get_question_sync, thread_sensitive=True)(application, code)

    async def _after_answer(self, chat_id: int, application: Application, context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Выполняет действие метода _after_answer."""
        logger.debug("_after_answer chat=%s application=%s", chat_id, application.pk)
        await sync_to_async(self._touch_activity, thread_sensitive=True)(application)
        await self._prompt_next_question(chat_id, application, context)

    async def _prompt_next_question(
        self,
        chat_id: int,
        application: Application,
        context: "ContextTypes.DEFAULT_TYPE",
    ) -> None:
        """Отправляет пользователю сообщение с очередным вопросом анкеты."""

        active = await self._resolve_active_question(application)
        if active is None:
            logger.debug("_prompt_next_question: no more questions")
            finish_text = (
                "Спасибо! Анкета заполнена. Мы свяжемся с вами после проверки данных.\n"
                "Вы можете оставить ещё одну заявку, нажав кнопку ниже."
            )
            InlineKeyboardButton, InlineKeyboardMarkup = _load_keyboard_classes()
            restart_markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton("Оставить ещё заявку", callback_data="__restart__")]]
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=finish_text,
                reply_markup=restart_markup,
            )
            return
        question = active.question
        logger.debug("Next question code=%s", question.code)
        prompt = self._render_question_prompt(question)
        markup = self._build_keyboard(question)
        if markup:
            await context.bot.send_message(chat_id=chat_id, text=prompt, reply_markup=markup)
        else:
            await context.bot.send_message(chat_id=chat_id, text=prompt)

    def _ensure_user_sync(self, telegram_user) -> Any:
        """Выполняет действие метода _ensure_user_sync."""
        UserModel = get_user_model()
        chat_id = telegram_user.id
        username = telegram_user.username
        now = timezone.now()
        logger.debug("_ensure_user_sync chat_id=%s username=%s", chat_id, username)
        user = UserModel.objects.filter(telegram_chat_id=chat_id).first()
        placeholder_email = f"telegram_{chat_id}@bot.local"
        if user is None:
            user = (
                UserModel.objects.filter(email=placeholder_email).first()
                or UserModel.objects.filter(telegram_username=username).first()
            )
            if user is None:
                user = UserModel.objects.create_user(
                    email=placeholder_email,
                    phone=None,
                    password=None,
                )
            user.telegram_chat_id = chat_id
            user.primary_platform = UserModel.Platform.TELEGRAM
        updates: list[str] = []
        if username and user.telegram_username != username:
            user.telegram_username = username
            updates.append("telegram_username")
        if user.telegram_chat_id != chat_id:
            user.telegram_chat_id = chat_id
            updates.append("telegram_chat_id")
        user.last_platform_used = UserModel.Platform.TELEGRAM
        user.last_telegram_activity = now
        updates.extend(["last_platform_used", "last_telegram_activity"])
        user.is_active = True
        updates.append("is_active")
        user.save(update_fields=list(dict.fromkeys(updates)))
        return user

    def _ensure_application_sync(self, user: Any) -> Application:
        """Выполняет действие метода _ensure_application_sync."""
        survey = Survey.objects.filter(code=self.survey_code, is_active=True).first()
        if survey is None:
            raise RuntimeError("Активная анкета не найдена")
        application = (
            Application.objects.filter(user=user, status=Application.Status.DRAFT, survey=survey)
            .select_related("current_step", "survey")
            .first()
        )
        if application:
            logger.debug("Existing draft application=%s", application.pk)
            return application
        first_step = survey.steps.order_by("order", "id").first()
        application = Application.objects.create(
            survey=survey,
            user=user,
            current_step=first_step,
            current_stage=first_step.order if first_step else 0,
        )
        logger.info("Создан черновик заявки %s для telegram-пользователя %s", application.public_id, user.pk)
        return application

    def _resolve_active_question_sync(self, application: Application) -> Optional[ActiveQuestion]:
        """Выполняет действие метода _resolve_active_question_sync."""
        answers = build_answer_dict(application)
        step = application.current_step
        if step is None:
            step = next_step(application.survey, None, answers)
            if step is not None:
                application.current_step = step
                application.current_stage = step.order
                application.save(update_fields=["current_step", "current_stage", "updated_at"])
        while step is not None:
            for question in visible_questions(step, answers):
                if self._auto_fill_question(application, question, answers):
                    continue
                if self._is_answer_missing(answers.get(question.code)):
                    logger.debug("Active question found=%s", question.code)
                    return ActiveQuestion(question=question, step=step, answers=answers)
            next_candidate = next_step(application.survey, step, answers)
            if next_candidate is None:
                return None
            application.current_step = next_candidate
            application.current_stage = next_candidate.order
            application.save(update_fields=["current_step", "current_stage", "updated_at"])
            step = next_candidate
        return None

    def _get_question_sync(self, application: Application, code: str) -> Optional[Question]:
        """Выполняет действие метода _get_question_sync."""
        return (
            Question.objects.filter(step__survey=application.survey, code=code)
            .select_related("step")
            .prefetch_related("options")
            .first()
        )

    def _save_answer_sync(self, application: Application, question: Question, value: Any) -> None:
        """Выполняет действие метода _save_answer_sync."""
        with transaction.atomic():
            Answer.objects.update_or_create(
                application=application,
                question=question,
                defaults={"value": value},
            )
            answers = build_answer_dict(application)
            ensure_applicant_account(application, answers)

    def _restart_application_sync(self, application: Application) -> Application:
        """Выполняет действие метода _restart_application_sync."""
        survey = application.survey
        user = application.user
        applicant_type = application.applicant_type

        Application.objects.filter(pk=application.pk).delete()

        consent_question = Question.objects.filter(step__survey=survey, code=CONSENT_QUESTION_CODE).first()
        basic_step = Step.objects.filter(survey=survey, code="s1_basic").first()
        if basic_step is None:
            basic_step = survey.steps.order_by("order", "id").first()

        new_application = Application.objects.create(
            survey=survey,
            user=user,
            current_step=basic_step,
            current_stage=basic_step.order if basic_step else 0,
            applicant_type=applicant_type,
        )

        if consent_question:
            Answer.objects.update_or_create(
                application=new_application,
                question=consent_question,
                defaults={"value": True},
            )
            if user:
                record_consent(
                    user=user,
                    application=new_application,
                    consent_type="pdn_152",
                    is_given=True,
                    ip_address=None,
                )

        return new_application

    async def _finalize_consent_decline(self, application: Application) -> None:
        """Выполняет действие метода _finalize_consent_decline."""
        await sync_to_async(handle_consent_decline, thread_sensitive=True)(application)

    async def _ingest_document(
        self,
        application: Application,
        question: Question,
        payload: dict[str, Any],
        context: "ContextTypes.DEFAULT_TYPE",
    ) -> str:
        """Выполняет действие метода _ingest_document."""
        filename, mime_type, content = await self._download_file(question, payload, context)
        size = len(content)
        requirement_code = self._requirement_code_for_question(question)
        document_id = await sync_to_async(
            self._store_document_binary,
            thread_sensitive=True,
        )(application, requirement_code, filename, mime_type, size, content)
        return document_id

    async def _download_file(
        self,
        question: Question,
        payload: dict[str, Any],
        context: "ContextTypes.DEFAULT_TYPE",
    ) -> tuple[str, str, bytes]:
        """Выполняет действие метода _download_file."""
        file_id = payload.get("file_id")
        if not file_id:
            raise DocumentIngestionError("Не удалось определить файл для загрузки.")
        try:
            telegram_file = await context.bot.get_file(file_id)
            byte_content = await telegram_file.download_as_bytearray()
        except Exception as exc:  # pragma: no cover - зависит от Telegram API
            logger.exception("Не удалось скачать файл из Telegram: %s", exc)
            raise DocumentIngestionError("Не удалось скачать файл из Telegram, попробуйте ещё раз.")
        filename = payload.get("file_name")
        if not filename:
            suffix = self._guess_extension(payload)
            filename = f"{question.code}_{payload.get('file_unique_id', 'upload')}{suffix}"
        mime_type = payload.get("mime_type") or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        return filename, mime_type, bytes(byte_content)

    def _store_document_binary(
        self,
        application: Application,
        requirement_code: Optional[str],
        filename: str,
        mime_type: str,
        size: int,
        content: bytes,
    ) -> str:
        """Выполняет действие метода _store_document_binary."""
        requirement = None
        if requirement_code:
            requirement = application.survey.doc_requirements.filter(code=requirement_code).first()
        logger.debug(
            "Storing document requirement=%s filename=%s size=%s",
            requirement_code,
            filename,
            size,
        )
        try:
            bundle = request_upload(
                application=application,
                requirement=requirement,
                document=None,
                filename=filename,
                content_type=mime_type,
                size=size,
                user=application.user,
            )
        except (ValidationError, DocumentStorageError) as exc:
            logger.warning("Ошибка при создании записи документа: %s", exc)
            raise DocumentIngestionError("Не удалось сохранить документ: файл не принят.") from exc
        storage = get_storage()
        try:
            storage.upload_bytes(key=bundle.version.file_key, content=content, content_type=mime_type)
        except DocumentStorageError as exc:  # pragma: no cover - зависит от инфраструктуры
            logger.exception("Ошибка загрузки в хранилище: %s", exc)
            raise DocumentIngestionError("Не удалось загрузить файл в хранилище.") from exc
        complete_upload(bundle.version)
        return str(bundle.document.public_id)

    def _touch_activity(self, application: Application) -> None:
        """Выполняет действие метода _touch_activity."""
        Application.objects.filter(pk=application.pk).update(updated_at=timezone.now())

    async def _validate_answer(self, question: Question, raw_value: Any) -> tuple[Any, Optional[str]]:
        """Выполняет действие метода _validate_answer."""
        return await sync_to_async(validate_answer_value, thread_sensitive=True)(question, raw_value)

    async def _prepare_freeform_input(self, question: Question, text: str) -> Tuple[Any, Optional[str]]:
        """Выполняет действие метода _prepare_freeform_input."""
        return await sync_to_async(self._prepare_freeform_input_sync, thread_sensitive=True)(question, text)

    def _prepare_freeform_input_sync(self, question: Question, text: str) -> Tuple[Any, Optional[str]]:
        """Выполняет действие метода _prepare_freeform_input_sync."""
        if question.type in {Question.QType.BOOLEAN, Question.QType.YES_NO}:
            mapped = self._map_boolean(text)
            if mapped is None:
                return None, "Ответьте «да» или «нет», либо воспользуйтесь кнопками."
            return mapped, None
        if question.type in {Question.QType.SELECT, Question.QType.SELECT_ONE}:
            mapped = self._map_option_value(question, text)
            if mapped is None:
                return None, "Выберите один из вариантов из списка ниже."
            return mapped, None
        if question.type in {Question.QType.MULTISELECT, Question.QType.SELECT_MANY}:
            options = self._map_multiple_options(question, text)
            if options is None:
                return None, "Перечислите варианты через запятую."
            return options, None
        if question.type == Question.QType.DATE:
            normalized = self._normalize_date(text)
            if normalized is None:
                return None, "Введите дату в формате ГГГГ-ММ-ДД или дд.мм.гггг."
            return normalized, None
        return text, None

    def _prepare_choice_input(self, question: Question, raw_value: str) -> Any:
        """Выполняет действие метода _prepare_choice_input."""
        if question.type in {Question.QType.BOOLEAN, Question.QType.YES_NO}:
            return raw_value.lower() in {"true", "1", "yes", "da"}
        if question.type in {Question.QType.MULTISELECT, Question.QType.SELECT_MANY}:
            return [raw_value]
        return raw_value

    def _build_keyboard(self, question: Question) -> Optional[Any]:
        """Выполняет действие метода _build_keyboard."""
        try:
            InlineKeyboardButton, InlineKeyboardMarkup = _load_keyboard_classes()
        except RuntimeError as exc:
            logger.warning("Не удалось построить клавиатуру: %s", exc)
            return None
        if question.type in {Question.QType.BOOLEAN, Question.QType.YES_NO}:
            buttons = [
                [InlineKeyboardButton("Да", callback_data=f"{question.code}|true")],
                [InlineKeyboardButton("Нет", callback_data=f"{question.code}|false")],
            ]
            return InlineKeyboardMarkup(buttons)
        if question.type in {Question.QType.SELECT, Question.QType.SELECT_ONE}:
            buttons: list[list[InlineKeyboardButton]] = []
            row: list[InlineKeyboardButton] = []
            for option in question.options.all():
                row.append(
                    InlineKeyboardButton(option.label, callback_data=f"{question.code}|{option.value}")
                )
                if len(row) == 2:
                    buttons.append(row)
                    row = []
            if row:
                buttons.append(row)
            if buttons:
                return InlineKeyboardMarkup(buttons)
        if question.type in {Question.QType.FILE, Question.QType.FILE_MULTI}:
            buttons = [
                [InlineKeyboardButton("Пропустить", callback_data=f"{question.code}|{SKIP_CALLBACK_VALUE}")],
            ]
            return InlineKeyboardMarkup(buttons)
        return None

    @staticmethod
    def _should_skip(text: str) -> bool:
        """Выполняет действие метода _should_skip."""
        lowered = text.lower()
        return lowered in {"пропустить", "skip", "позже"}

    @staticmethod
    def _is_answer_missing(value: Any) -> bool:
        """Выполняет действие метода _is_answer_missing."""
        return value in (None, "", [], {})

    @staticmethod
    def _parse_callback_payload(payload: str) -> Tuple[Optional[str], Optional[str]]:
        """Выполняет действие метода _parse_callback_payload."""
        if "|" not in payload:
            return None, None
        return tuple(payload.split("|", 1))  # type: ignore[return-value]

    @staticmethod
    def _map_boolean(text: str) -> Optional[bool]:
        """Выполняет действие метода _map_boolean."""
        normalized = text.strip().lower()
        if normalized in {"да", "д", "yes", "y", "true", "1"}:
            return True
        if normalized in {"нет", "н", "no", "n", "false", "0"}:
            return False
        return None

    @staticmethod
    def _normalize_date(text: str) -> Optional[str]:
        """Выполняет действие метода _normalize_date."""
        cleaned = text.strip()
        for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(cleaned, fmt).date().isoformat()
            except ValueError:
                continue
        return None

    @staticmethod
    def _map_option_value(question: Question, text: str) -> Optional[str]:
        """Выполняет действие метода _map_option_value."""
        token = text.strip().lower()
        for option in question.options.all():
            if token == option.value.lower() or token == option.label.lower():
                return option.value
        return None

    @staticmethod
    def _map_multiple_options(question: Question, text: str) -> Optional[list[str]]:
        """Выполняет действие метода _map_multiple_options."""
        items = [part.strip() for part in text.split(",") if part.strip()]
        if not items:
            return None
        mapped: list[str] = []
        for item in items:
            value = DefaultScenario._map_option_value(question, item)
            if value is None:
                return None
            if value not in mapped:
                mapped.append(value)
        return mapped

    @staticmethod
    def _extract_file_payload(message: Any) -> Optional[dict[str, Any]]:
        """Выполняет действие метода _extract_file_payload."""
        if message.document:
            document = message.document
            return {
                "type": "document",
                "file_id": document.file_id,
                "file_unique_id": document.file_unique_id,
                "file_name": document.file_name,
                "mime_type": document.mime_type,
                "file_size": document.file_size,
            }
        if message.photo:
            photo = message.photo[-1]
            return {
                "type": "photo",
                "file_id": photo.file_id,
                "file_unique_id": photo.file_unique_id,
                "width": photo.width,
                "height": photo.height,
                "file_size": photo.file_size,
                "mime_type": "image/jpeg",
            }
        if message.audio:
            audio = message.audio
            return {
                "type": "audio",
                "file_id": audio.file_id,
                "file_unique_id": audio.file_unique_id,
                "title": audio.title,
                "performer": audio.performer,
                "file_size": audio.file_size,
                "mime_type": getattr(audio, "mime_type", None),
                "file_name": getattr(audio, "file_name", None),
            }
        return None

    @staticmethod
    def _guess_extension(payload: dict[str, Any]) -> str:
        """Выполняет действие метода _guess_extension."""
        payload_type = payload.get("type")
        if payload_type == "photo":
            return ".jpg"
        if payload_type == "audio":
            return ".mp3"
        return ".bin"

    @staticmethod
    def _requirement_code_for_question(question: Question) -> Optional[str]:
        """Выполняет действие метода _requirement_code_for_question."""
        code = question.code
        if code.startswith("q_doc_"):
            return code.removeprefix("q_doc_")
        if code == "q_doc_photos_multi":
            return "photos_multi"
        return None

    def _render_question_prompt(self, question: Question) -> str:
        """Выполняет действие метода _render_question_prompt."""
        parts: list[str] = [question.label]
        payload = question.payload or {}
        help_text = payload.get("help_text")

        if question.type in {Question.QType.MULTISELECT, Question.QType.SELECT, Question.QType.SELECT_ONE}:
            prefetched = getattr(question, "_prefetched_objects_cache", {}).get("options")
            options = list(prefetched) if prefetched is not None else list(question.options.all())
            if options:
                option_lines = [f"- {option.label}" for option in options]
                if question.type == Question.QType.MULTISELECT:
                    parts.append("")
                    parts.append("Выберите подходящие варианты и отправьте их через запятую.")
                parts.append("")
                parts.extend(option_lines)
        elif question.type in {Question.QType.FILE, Question.QType.FILE_MULTI}:
            parts.append("")
            parts.append("Отправьте документ одним сообщением. Если его нет под рукой, нажмите «Пропустить».")
        elif question.type in {Question.QType.BOOLEAN, Question.QType.YES_NO}:
            parts.append("")
            parts.append("Выберите ответ с помощью кнопок ниже.")

        if help_text:
            parts.append("")
            parts.append(help_text)

        return "\n".join(filter(None, parts))

    def _auto_fill_question(self, application: Application, question: Question, answers: dict[str, Any]) -> bool:
        """Выполняет действие метода _auto_fill_question."""
        payload = question.payload or {}
        if payload.get("hidden") and question.type != Question.QType.FILE and question.type != Question.QType.FILE_MULTI:
            # hidden non-file questions should be auto-filled if possible
            if question.type == Question.QType.DATE and question.code in AUTO_FILL_DATE_QUESTIONS:
                today = date.today().isoformat()
                Answer.objects.update_or_create(
                    application=application,
                    question=question,
                    defaults={"value": today},
                )
                answers[question.code] = today
                return True
            if question.code in answers:
                return True
        if question.type == Question.QType.DATE and question.code in AUTO_FILL_DATE_QUESTIONS:
            if self._is_answer_missing(answers.get(question.code)):
                today = date.today().isoformat()
                Answer.objects.update_or_create(
                    application=application,
                    question=question,
                    defaults={"value": today},
                )
                answers[question.code] = today
                return True
        return False


def _load_keyboard_classes():
    """Выполняет действие метода _load_keyboard_classes."""
    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup  # type: ignore
    except ImportError as exc:  # pragma: no cover - dependency missing only at runtime
        raise RuntimeError("python-telegram-bot не установлен") from exc
    return InlineKeyboardButton, InlineKeyboardMarkup


__all__ = ["DefaultScenario", "ActiveQuestion"]
