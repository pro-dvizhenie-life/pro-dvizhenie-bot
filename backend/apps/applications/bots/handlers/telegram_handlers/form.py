import datetime
import logging

from telegram import Update
from telegram.ext import ContextTypes

from ..database import init_telegram_db
from ..telegram_models import TelegramUser as User
from ..telegram_models import UserState
from .keyboards import (
    applicant_status_keyboard,
    gender_keyboard,
    product_keyboard,
    yes_no_keyboard,
)

logger = logging.getLogger(__name__)

# Инициализация БД
SessionLocal = init_telegram_db()

def get_or_create_user(chat_id: int) -> User:
    """Получает или создает пользователя в БД."""
    try:
        with SessionLocal() as db:
            user = db.get(User, chat_id)
            if not user:
                user = User(chat_id=chat_id, state=UserState.START)
                db.add(user)
                db.commit()
                db.refresh(user)
                logger.info(f"Создан новый пользователь: {chat_id}")
            return user
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя {chat_id}: {e}")
        raise

def save_user(user: User):
    """Сохраняет пользователя в БД."""
    try:
        with SessionLocal() as db:
            db.merge(user)
            db.commit()
            logger.debug(f"Пользователь {user.chat_id} сохранен")
    except Exception as e:
        logger.error(f"Ошибка при сохранении пользователя {user.chat_id}: {e}")
        raise

async def form_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = get_or_create_user(chat_id)
    if user.state == UserState.START:
        user.state = UserState.WAITING_FOR_CONSENT
        save_user(user)
        await update.message.reply_text(
            "Чтобы продолжить, необходимо согласиться с условиями и дать согласие на обработку персональных данных (152-ФЗ).",
            reply_markup=yes_no_keyboard()
        )
    else:
        await update.message.reply_text(
            "Вы уже начали или завершили заполнение анкеты. Для продолжения используйте /start или /help."
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    user = get_or_create_user(chat_id)
    data = query.data
    if user.state == UserState.WAITING_FOR_CONSENT:
        if data == "YES":
            user.confirmed_agreement = True
            user.state = UserState.WAITING_FOR_APPLICANT_STATUS
            save_user(user)
            await query.answer()
            await query.edit_message_text(
                "Спасибо за согласие! Укажите, кто вы:",
                reply_markup=applicant_status_keyboard()
            )
        elif data == "NO":
            user.confirmed_agreement = False
            user.state = UserState.START
            save_user(user)
            await query.answer()
            await query.edit_message_text(
                "Без согласия на обработку персональных данных продолжить невозможно.",
                reply_markup=None
            )
    elif user.state == UserState.WAITING_FOR_APPLICANT_STATUS:
        if data in ["APPLICANT_SELF", "APPLICANT_PARENT", "APPLICANT_GUARDIAN", "APPLICANT_RELATIVE"]:
            user.applicant_status = data
            user.state = UserState.WAITING_FOR_CONTACT_PERSON
            save_user(user)
            await query.answer()
            await query.edit_message_text(
                "Укажите контактное лицо (ФИО):",
                reply_markup=None
            )
    elif user.state == UserState.WAITING_FOR_GENDER:
        if data in ["GENDER_MALE", "GENDER_FEMALE"]:
            user.gender = "Мужской" if data == "GENDER_MALE" else "Женский"
            user.state = UserState.WAITING_FOR_CITY
            save_user(user)
            await query.answer()
            await query.edit_message_text(
                "Введите город проживания:",
                reply_markup=None
            )
    elif user.state == UserState.WAITING_FOR_PRODUCT:
        if data in ["PRODUCT_WHEELCHAIR", "PRODUCT_CONSOLE", "PRODUCT_PARTS"]:
            if data == "PRODUCT_WHEELCHAIR":
                user.product = "Коляска (ТСР)"
            elif data == "PRODUCT_CONSOLE":
                user.product = "Приставка"
            elif data == "PRODUCT_PARTS":
                user.product = "Комплектующие"
            user.state = UserState.WAITING_FOR_CERTIFICATE
            save_user(user)
            await query.answer()
            await query.edit_message_text(
                "Есть ли сертификат на ТСР?", reply_markup=yes_no_keyboard()
            )
    elif user.state == UserState.WAITING_FOR_CERTIFICATE:
        if data == "YES":
            user.has_certificate = True
            user.state = UserState.WAITING_FOR_CERTIFICATE_NUMBER
            save_user(user)
            await query.answer()
            await query.edit_message_text("Укажите номер сертификата:")
        elif data == "NO":
            user.has_certificate = False
            user.state = UserState.WAITING_FOR_OTHER_FUNDRAISING
            save_user(user)
            await query.answer()
            await query.edit_message_text("Есть ли открытые сборы в других фондах?", reply_markup=yes_no_keyboard())
    elif user.state == UserState.WAITING_FOR_OTHER_FUNDRAISING:
        if data == "YES":
            user.has_other_fundraising = True
            user.state = UserState.WAITING_FOR_OTHER_FUNDRAISING_DETAILS
            save_user(user)
            await query.answer()
            await query.edit_message_text("Укажите фонд, цель и ссылку на сбор:")
        elif data == "NO":
            user.has_other_fundraising = False
            user.state = UserState.WAITING_FOR_CONSULTATION
            save_user(user)
            await query.answer()
            await query.edit_message_text(
                "Нужна ли вам консультационная помощь в составлении рекомендаций ИПРА, прохождении МСЭ, получении ТСР от СФР? Ответьте текстом."
            )
    elif user.state == UserState.WAITING_FOR_CONSULTATION:
        await query.edit_message_text(
            "Напишите текстом, нужна ли консультационная помощь по ИПРА, МСЭ или ТСР от СФР."
        )
        await query.answer()
    elif user.state == UserState.WAITING_FOR_CAN_PROMOTE:
        if data == "YES":
            user.can_promote = True
            user.state = UserState.WAITING_FOR_PROMOTION_LINKS
            save_user(user)
            await query.answer()
            await query.edit_message_text("Укажите ссылки на соцсети/медиа:")
        elif data == "NO":
            user.can_promote = False
            user.state = UserState.WAITING_FOR_POSITIONING_INFO
            save_user(user)
            await query.answer()
            await query.edit_message_text("Хотели бы получать информацию о правильном позиционировании?", reply_markup=yes_no_keyboard())
    elif user.state == UserState.WAITING_FOR_POSITIONING_INFO:
        if data == "YES":
            user.wants_positioning_info = True
        elif data == "NO":
            user.wants_positioning_info = False
        user.state = UserState.WAITING_FOR_PHOTO
        save_user(user)
        await query.answer()
        await query.edit_message_text("Пожалуйста, отправьте фотографию одним сообщением.")
    elif user.state == UserState.WAITING_FOR_VIDEO:
        if data == "YES":
            user.wants_video = True
        elif data == "NO":
            user.wants_video = False
        user.state = UserState.WAITING_FOR_ADDITIONAL_INFO
        save_user(user)
        await query.answer()
        await query.edit_message_text("Хотите добавить что-то от себя?")
    elif user.state == UserState.WAITING_FOR_GOSUSLUGI_CONFIRMATION:
        if data == "YES":
            user.has_gosuslugi = True
        elif data == "NO":
            user.has_gosuslugi = False
        user.state = UserState.WAITING_FOR_DOCUMENTS
        save_user(user)
        await query.answer()
        await query.edit_message_text(
            "Отлично! Теперь загрузите документы:\n\n1️⃣ Паспорт (разворот с фото)\n2️⃣ СНИЛС\n3️⃣ Свидетельство о рождении ребенка (если актуально)\n4️⃣ ИПРА (если есть)\n\nОтправляйте документы по одному. Когда закончите, напишите 'готово'."
        )
    # TODO: обработка следующих этапов анкеты

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = get_or_create_user(chat_id)
    text = update.message.text.strip()
    if user.state == UserState.WAITING_FOR_CONTACT_PERSON:
        user.contact_person = text
        user.state = UserState.WAITING_FOR_FULL_NAME
        save_user(user)
        await update.message.reply_text("Введите ФИО подопечного:")
    elif user.state == UserState.WAITING_FOR_FULL_NAME:
        user.full_name = text
        user.state = UserState.WAITING_FOR_BIRTH_DATE
        save_user(user)
        await update.message.reply_text("Введите дату рождения в формате дд.мм.гггг:")
    elif user.state == UserState.WAITING_FOR_BIRTH_DATE:
        try:
            birthday = datetime.datetime.strptime(text, "%d.%m.%Y")
            user.birthday = birthday
            user.state = UserState.WAITING_FOR_GENDER
            save_user(user)
            await update.message.reply_text("Выберите пол:", reply_markup=gender_keyboard())
        except ValueError:
            await update.message.reply_text("Некорректный формат даты. Введите в формате дд.мм.гггг:")
    elif user.state == UserState.WAITING_FOR_CITY:
        user.city = text
        user.state = UserState.WAITING_FOR_PHONE
        save_user(user)
        await update.message.reply_text("Введите телефон в формате +7XXXXXXXXXX:")
    elif user.state == UserState.WAITING_FOR_PHONE:
        user.phone = text
        user.state = UserState.WAITING_FOR_EMAIL
        save_user(user)
        await update.message.reply_text("Введите email:")
    elif user.state == UserState.WAITING_FOR_EMAIL:
        user.email = text
        user.state = UserState.WAITING_FOR_PRODUCT
        save_user(user)
        await update.message.reply_text("Что нужно приобрести?", reply_markup=product_keyboard())
    # --- Этап 1: сертификат ---
    elif user.state == UserState.WAITING_FOR_CERTIFICATE_NUMBER:
        user.certificate_number = text
        user.state = UserState.WAITING_FOR_CERTIFICATE_AMOUNT
        save_user(user)
        await update.message.reply_text("Укажите сумму сертификата:")
    elif user.state == UserState.WAITING_FOR_CERTIFICATE_AMOUNT:
        user.certificate_amount = text
        user.state = UserState.WAITING_FOR_CERTIFICATE_EXPIRY
        save_user(user)
        await update.message.reply_text(
            "Введите дату окончания действия сертификата (ГГГГ-ММ-ДД или дд.мм.гггг):"
        )
    elif user.state == UserState.WAITING_FOR_CERTIFICATE_EXPIRY:
        user.certificate_expiry = text
        user.state = UserState.WAITING_FOR_OTHER_FUNDRAISING
        save_user(user)
        await update.message.reply_text("Есть ли открытые сборы в других фондах?", reply_markup=yes_no_keyboard())
    elif user.state == UserState.WAITING_FOR_OTHER_FUNDRAISING_DETAILS:
        user.other_fundraising_details = text
        user.state = UserState.WAITING_FOR_CONSULTATION
        save_user(user)
        await update.message.reply_text(
            "Нужна ли вам консультационная помощь в составлении рекомендаций ИПРА, прохождении МСЭ, получении ТСР от СФР? Ответьте текстом."
        )
    elif user.state == UserState.WAITING_FOR_CONSULTATION:
        user.needs_consultation = text
        user.state = UserState.WAITING_FOR_CAN_PROMOTE
        save_user(user)
        await update.message.reply_text("Есть ли возможность продвигать сбор самостоятельно?", reply_markup=yes_no_keyboard())
    elif user.state == UserState.WAITING_FOR_PROMOTION_LINKS:
        user.promotion_links = text
        user.state = UserState.WAITING_FOR_POSITIONING_INFO
        save_user(user)
        await update.message.reply_text("Хотели бы получать информацию о правильном позиционировании?", reply_markup=yes_no_keyboard())
    # --- Этап 2: История подопечного ---
    elif user.state == UserState.WAITING_FOR_DIAGNOSIS:
        user.diagnosis = text
        user.state = UserState.WAITING_FOR_HEALTH_CONDITION
        save_user(user)
        await update.message.reply_text("Опишите текущее состояние здоровья и ограничения:")
    elif user.state == UserState.WAITING_FOR_HEALTH_CONDITION:
        user.health_condition = text
        user.state = UserState.WAITING_FOR_DIAGNOSIS_DATE
        save_user(user)
        await update.message.reply_text("Когда был поставлен диагноз?")
    elif user.state == UserState.WAITING_FOR_DIAGNOSIS_DATE:
        user.diagnosis_date = text
        user.state = UserState.WAITING_FOR_TSR_PRESCRIPTION
        save_user(user)
        await update.message.reply_text("Прописано ли ТСР в медзаключении или ИПРА?")
    elif user.state == UserState.WAITING_FOR_TSR_PRESCRIPTION:
        user.has_tsr_prescription = text
        user.state = UserState.WAITING_FOR_DEADLINE
        save_user(user)
        await update.message.reply_text("Есть ли сроки, к которым особенно важно получить помощь?")
    elif user.state == UserState.WAITING_FOR_DEADLINE:
        user.deadline = text
        # Определяем возраст и выбираем ветку
        if user.birthday:
            age = (datetime.datetime.now() - user.birthday).days // 365
            if age >= 18:
                # Ветка A: Взрослый
                user.state = UserState.WAITING_FOR_FAMILY_INFO
                save_user(user)
                await update.message.reply_text("Расскажите о семье или близких, кто рядом и поддерживает:")
            else:
                # Ветка B: Ребенок
                user.state = UserState.WAITING_FOR_FAMILY_COMPOSITION
                save_user(user)
                await update.message.reply_text("Расскажите о семье: кто входит, чем занимаются родители/опекуны:")
        else:
            # По умолчанию взрослый
            user.state = UserState.WAITING_FOR_FAMILY_INFO
            save_user(user)
            await update.message.reply_text("Расскажите о семье или близких, кто рядом и поддерживает:")
    elif user.state == UserState.WAITING_FOR_WHY_NEEDED:
        user.why_needed = text
        user.state = UserState.WAITING_FOR_MESSAGE_TO_DONORS
        save_user(user)
        await update.message.reply_text("Что бы вы хотели сказать людям, которые прочитают вашу историю?")
    elif user.state == UserState.WAITING_FOR_MESSAGE_TO_DONORS:
        user.message_to_donors = text
        user.state = UserState.WAITING_FOR_VIDEO
        save_user(user)
        await update.message.reply_text("Готовы ли записать короткое видео о своей жизни?", reply_markup=yes_no_keyboard())
    elif user.state == UserState.WAITING_FOR_ADDITIONAL_INFO:
        user.additional_info = text
        user.state = UserState.WAITING_FOR_GOSUSLUGI_CONFIRMATION
        save_user(user)
        await update.message.reply_text("Этап 2 завершён. Переходим к Этапу 3 - Документы.\n\nВы зарегистрированы на портале Госуслуг?", reply_markup=yes_no_keyboard())
    # --- Ветка A: Взрослый ---
    elif user.state == UserState.WAITING_FOR_FAMILY_INFO:
        user.family_info = text
        user.state = UserState.WAITING_FOR_INSPIRATION
        save_user(user)
        await update.message.reply_text("Кто вас вдохновляет или поддерживает?")
    elif user.state == UserState.WAITING_FOR_INSPIRATION:
        user.inspiration = text
        user.state = UserState.WAITING_FOR_HOBBIES
        save_user(user)
        await update.message.reply_text("Чем увлекаетесь? Есть ли любимое хобби?")
    elif user.state == UserState.WAITING_FOR_HOBBIES:
        user.hobbies = text
        user.state = UserState.WAITING_FOR_ACHIEVEMENTS
        save_user(user)
        await update.message.reply_text("Какие успехи или достижения особенно дороги?")
    elif user.state == UserState.WAITING_FOR_ACHIEVEMENTS:
        user.achievements = text
        user.state = UserState.WAITING_FOR_WHY_NEEDED
        save_user(user)
        await update.message.reply_text("Почему нужна новая коляска/приставка/комплектующее?")
    # --- Ветка B: Ребенок ---
    elif user.state == UserState.WAITING_FOR_FAMILY_COMPOSITION:
        user.family_composition = text
        user.state = UserState.WAITING_FOR_SIBLINGS_PETS
        save_user(user)
        await update.message.reply_text("Есть ли у ребенка братья/сестры, домашние питомцы?")
    elif user.state == UserState.WAITING_FOR_SIBLINGS_PETS:
        user.siblings_pets = text
        user.state = UserState.WAITING_FOR_FAMILY_TRADITIONS
        save_user(user)
        await update.message.reply_text("Какие традиции или важные совместные занятия есть у семьи?")
    elif user.state == UserState.WAITING_FOR_FAMILY_TRADITIONS:
        user.family_traditions = text
        user.state = UserState.WAITING_FOR_CHILD_HOBBIES
        save_user(user)
        await update.message.reply_text("Чем увлекается ребенок, какие хобби или интересы?")
    elif user.state == UserState.WAITING_FOR_CHILD_HOBBIES:
        user.child_hobbies = text
        user.state = UserState.WAITING_FOR_CHILD_DREAM
        save_user(user)
        await update.message.reply_text("Какая мечта у ребенка?")
    elif user.state == UserState.WAITING_FOR_CHILD_DREAM:
        user.child_dream = text
        user.state = UserState.WAITING_FOR_WHY_NEEDED
        save_user(user)
        await update.message.reply_text("Почему нужна коляска/приставка/комплектующие?")
    # --- фото ---
    elif user.state == UserState.WAITING_FOR_PHOTO:
        await update.message.reply_text("Пожалуйста, отправьте фотографию одним сообщением.")
    # TODO: обработка следующих этапов анкеты
