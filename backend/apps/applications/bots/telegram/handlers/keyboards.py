from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def yes_no_keyboard():
    """Выполняет действие метода yes_no_keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Да", callback_data="YES"),
            InlineKeyboardButton("❌ Нет", callback_data="NO")
        ]
    ])

def resume_keyboard():
    """Выполняет действие метода resume_keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Продолжить", callback_data="RESUME_BUTTON"),
            InlineKeyboardButton("Начать заново", callback_data="RESTART_BUTTON")
        ]
    ])

def product_keyboard():
    """Выполняет действие метода product_keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Коляска (ТСР)", callback_data="PRODUCT_WHEELCHAIR"),
            InlineKeyboardButton("Приставка", callback_data="PRODUCT_CONSOLE"),
            InlineKeyboardButton("Комплектующие", callback_data="PRODUCT_PARTS")
        ]
    ])

def applicant_status_keyboard():
    """Выполняет действие метода applicant_status_keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Я и есть подопечный", callback_data="APPLICANT_SELF"),
            InlineKeyboardButton("Мать/отец", callback_data="APPLICANT_PARENT")
        ],
        [
            InlineKeyboardButton("Опекун", callback_data="APPLICANT_GUARDIAN"),
            InlineKeyboardButton("Родственник", callback_data="APPLICANT_RELATIVE")
        ]
    ])

def gender_keyboard():
    """Выполняет действие метода gender_keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Мужской", callback_data="GENDER_MALE"),
            InlineKeyboardButton("Женский", callback_data="GENDER_FEMALE")
        ]
    ])
