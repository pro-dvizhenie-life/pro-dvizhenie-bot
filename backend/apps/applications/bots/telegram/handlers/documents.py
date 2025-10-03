import logging

from telegram import Update
from telegram.ext import ContextTypes

from ..database import init_telegram_db
from ..models import TelegramUser as User
from ..models import UserState
from .form import get_or_create_user, save_user
from .preview import send_preview

logger = logging.getLogger(__name__)

# Инициализация БД
SessionLocal = init_telegram_db()


async def handle_documents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает загрузку документов и команду завершения."""
    chat_id = update.effective_chat.id
    user = get_or_create_user(chat_id)

    if user.state != UserState.WAITING_FOR_DOCUMENTS:
        return

    # Проверяем, написал ли пользователь "готово"
    if update.message.text and update.message.text.strip().lower() == "готово":
        user.state = UserState.PREVIEW
        save_user(user)
        await send_preview(update, user)
        return

    # Обработка документа (фото или файл)
    if update.message.photo:
        await process_document_photo(update, user)
    elif update.message.document:
        await process_document_file(update, user)
    else:
        await update.message.reply_text("Пожалуйста, отправьте документ в виде фото или файла.")


async def process_document_photo(update: Update, user: User):
    """Сохраняет фотографию документа и уведомляет пользователя."""
    try:
        # Получаем фото с наилучшим качеством
        photo = update.message.photo[-1]
        file_id = photo.file_id

        # Получаем файл через бота
        bot = update.get_bot()
        file = await bot.get_file(file_id)
        file_data = await file.download_as_bytearray()

        # Сохраняем документ
        save_document(user, file_data)
        await update.message.reply_text("Документ принят. Загрузите следующий или напишите 'готово'.")

    except Exception as e:
        logger.error(f"Ошибка при загрузке документа: {e}")
        await update.message.reply_text("Произошла ошибка при загрузке документа. Попробуйте ещё раз.")


async def process_document_file(update: Update, user: User):
    """Сохраняет присланный файл документа и уведомляет пользователя."""
    try:
        document = update.message.document
        file_id = document.file_id

        # Получаем файл через бота
        bot = update.get_bot()
        file = await bot.get_file(file_id)
        file_data = await file.download_as_bytearray()

        # Сохраняем документ
        save_document(user, file_data)
        await update.message.reply_text("Документ принят. Загрузите следующий или напишите 'готово'.")

    except Exception as e:
        logger.error(f"Ошибка при загрузке документа: {e}")
        await update.message.reply_text("Произошла ошибка при загрузке документа. Попробуйте ещё раз.")


def save_document(user: User, document_data: bytes):
    """Сохраняет документ в первый свободный слот профиля."""
    if user.passport_data is None:
        user.passport_data = document_data
        logger.info(f"Сохранён паспорт для пользователя {user.chat_id}")
    elif user.snils_data is None:
        user.snils_data = document_data
        logger.info(f"Сохранён СНИЛС для пользователя {user.chat_id}")
    elif user.birth_certificate_data is None:
        user.birth_certificate_data = document_data
        logger.info(f"Сохранено свидетельство о рождении для пользователя {user.chat_id}")
    elif user.ipra_data is None:
        user.ipra_data = document_data
        logger.info(f"Сохранена ИПРА для пользователя {user.chat_id}")
    else:
        logger.info(f"Все слоты документов заполнены для пользователя {user.chat_id}")

    save_user(user)
