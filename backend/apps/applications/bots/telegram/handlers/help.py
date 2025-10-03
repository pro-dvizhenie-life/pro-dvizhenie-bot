from telegram import Update
from telegram.ext import ContextTypes


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
📋 Доступные команды:

/start - Начать работу с ботом
/help - Показать эту справку
/form - Начать заполнение анкеты
/anketa - Альтернативная команда для анкеты

📝 Процесс заполнения анкеты:
1. Согласие на обработку данных
2. Информация о заявителе
3. Контактные данные
4. Информация о продукте
5. Медицинская информация
6. Загрузка документов

⏱️ Заполнение займет 15-20 минут.
Вы можете прерваться и продолжить позже.

📞 Если возникнут вопросы, обратитесь в поддержку фонда.
    """

    await update.message.reply_text(help_text.strip())
