from telegram import Update
from telegram.ext import ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_text = """
🤖 Добро пожаловать в бот фонда «Движение Жизни»!

Я помогу вам заполнить заявку на получение помощи.

Для начала работы используйте команды:
/start - начать работу
/help - получить справку  
/form - начать заполнение анкеты

Наши специалисты свяжутся с вами после заполнения анкеты.
    """

    await update.message.reply_text(welcome_text.strip())
