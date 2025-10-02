from telegram import Update
from telegram.ext import ContextTypes
import logging

from ....bots.telegram_models import TelegramUser as User, UserState
from ....bots.database import init_telegram_db
from .form import get_or_create_user, save_user
from .keyboards import resume_keyboard

logger = logging.getLogger(__name__)

# Инициализация БД
SessionLocal = init_telegram_db()


async def send_preview(update: Update, user: User):
    """Отправляет предпросмотр анкеты с кнопками"""
    preview_text = f"""*Предпросмотр вашей заявки:*

*ФИО:* {user.full_name or '-'}
*Дата рождения:* {user.birthday.strftime('%d.%m.%Y') if user.birthday else '-'}
*Пол:* {user.gender or '-'}
*Город:* {user.city or '-'}
*Телефон:* {user.phone or '-'}
*Email:* {user.email or '-'}
*Продукт:* {user.product or '-'}
*Диагноз:* {user.diagnosis or '-'}

Все данные сохранены. Наши специалисты свяжутся с вами в ближайшее время.

Спасибо за заполнение анкеты!

Вы можете начать заполнение анкеты заново или оставить как есть."""

    await update.message.reply_text(
        preview_text,
        parse_mode='Markdown',
        reply_markup=resume_keyboard()
    )

    # Переводим пользователя в состояние COMPLETED
    user.state = UserState.COMPLETED
    save_user(user)


async def handle_preview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает кнопки в предпросмотре"""
    query = update.callback_query
    chat_id = query.message.chat_id
    user = get_or_create_user(chat_id)
    data = query.data

    if data == "RESUME_BUTTON":
        # Продолжить - ничего не делаем, анкета уже завершена
        await query.answer()
        await query.edit_message_text("Ваша анкета уже завершена. Мы свяжемся с вами после проверки заявки.")
    elif data == "RESTART_BUTTON":
        # Начать заново - сбрасываем все данные
        user.state = UserState.START
        # Очищаем все поля (кроме chat_id)
        for field in ['full_name', 'birthday', 'gender', 'contact_person', 'phone', 'email',
                      'city', 'product', 'applicant_status', 'has_certificate', 'certificate_number',
                      'certificate_amount', 'certificate_expiry', 'has_other_fundraising',
                      'other_fundraising_details', 'needs_consultation', 'can_promote',
                      'promotion_links', 'wants_positioning_info', 'diagnosis', 'health_condition',
                      'diagnosis_date', 'has_tsr_prescription', 'deadline', 'why_needed',
                      'message_to_donors', 'wants_video', 'additional_info', 'family_info',
                      'inspiration', 'hobbies', 'achievements', 'family_composition',
                      'siblings_pets', 'family_traditions', 'child_hobbies', 'child_dream',
                      'image_data', 'has_gosuslugi', 'passport_data', 'snils_data',
                      'birth_certificate_data', 'ipra_data']:
            setattr(user, field, None)

        save_user(user)
        await query.answer()
        await query.edit_message_text(
            "Анкета сброшена. Для начала заполнения используйте /start."
        )
